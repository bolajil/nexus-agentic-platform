# NEXUS Platform — Production Cloud Deployment Guide

Production-grade deployment for AWS (EKS), GCP (GKE), and Azure (AKS).
All three paths share the same Kubernetes manifests in `infra/k8s/`.

---

## Architecture Overview

```
                    ┌─────────────────────────────────────────────┐
                    │              DNS / CDN Layer                  │
                    │  Route 53 / Cloud DNS / Azure DNS             │
                    │  + CloudFront / Cloud CDN / Azure Front Door  │
                    └──────────────────┬──────────────────────────┘
                                       │ HTTPS (TLS 1.3)
                    ┌──────────────────▼──────────────────────────┐
                    │           Load Balancer + WAF                 │
                    │  AWS ALB+WAFv2 / GCP HTTPS LB / Azure AppGW  │
                    └──────────────────┬──────────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────────┐
                    │           Kubernetes (EKS/GKE/AKS)           │
                    │  ┌────────────┐   ┌──────────────────────┐  │
                    │  │  Frontend  │   │       Backend         │  │
                    │  │  2–10 pods │   │      3–20 pods        │  │
                    │  │  Next.js   │   │      FastAPI          │  │
                    │  └────────────┘   └──────────┬───────────┘  │
                    │                              │               │
                    │  ┌───────────┐  ┌────────────▼────────────┐ │
                    │  │ ChromaDB  │  │   Redis (Session Store)  │ │
                    │  │ (VectorDB)│  │  ElastiCache/Memorystore │ │
                    │  └───────────┘  └─────────────────────────┘ │
                    └─────────────────────────────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────────┐
                    │           Observability Stack                  │
                    │  Prometheus + Grafana + Alertmanager           │
                    │  CloudWatch / Cloud Monitoring / Azure Monitor │
                    │  Langfuse (LLM tracing)                        │
                    └─────────────────────────────────────────────┘
```

---

## Prerequisites (All Platforms)

```bash
# Install tools
brew install terraform kubectl helm awscli azure-cli google-cloud-sdk

# Verify versions
terraform --version    # >= 1.7.0
kubectl version --client
helm version           # >= 3.14
```

---

## 1. AWS — EKS Deployment

### A. Bootstrap Terraform State

```bash
# Create S3 bucket for Terraform state (one-time)
aws s3api create-bucket \
  --bucket nexus-terraform-state \
  --region us-east-1

aws s3api put-bucket-versioning \
  --bucket nexus-terraform-state \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket nexus-terraform-state \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms"}}]}'

# DynamoDB for state locking
aws dynamodb create-table \
  --table-name nexus-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### B. Provision Infrastructure

```bash
cd infra/aws

# Pass secrets via environment variables (never in tfvars files)
export TF_VAR_openai_api_key="sk-..."
export TF_VAR_langfuse_public_key="pk-lf-..."
export TF_VAR_langfuse_secret_key="sk-lf-..."
export TF_VAR_redis_auth_token="$(openssl rand -base64 32)"
export TF_VAR_domain_name="nexus.yourdomain.com"

terraform init
terraform plan -out=tfplan
terraform apply tfplan

# Save outputs
terraform output -json > ../aws-outputs.json
```

### C. Configure kubectl

```bash
aws eks update-kubeconfig \
  --region us-east-1 \
  --name nexus-production

kubectl get nodes   # verify cluster is reachable
```

### D. Install EKS Add-ons via Helm

```bash
# AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts && helm repo update
helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  --namespace kube-system \
  --set clusterName=nexus-production \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=\
    $(terraform -chdir=infra/aws output -raw lb_controller_role_arn)

# EFS CSI Driver StorageClass
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: $(terraform -chdir=infra/aws output -raw efs_file_system_id)
  directoryPerms: "700"
EOF

# GP3 StorageClass (default)
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
EOF
```

### E. Build and Push Docker Images

```bash
# Login to ECR
ECR_BACKEND=$(terraform -chdir=infra/aws output -raw ecr_backend_url)
ECR_FRONTEND=$(terraform -chdir=infra/aws output -raw ecr_frontend_url)
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin ${ECR_BACKEND%%/*}

# Build and push backend
docker build -t nexus-backend:v1.0.0 ./backend
docker tag nexus-backend:v1.0.0 ${ECR_BACKEND}:v1.0.0
docker push ${ECR_BACKEND}:v1.0.0

# Build and push frontend
docker build -t nexus-frontend:v1.0.0 ./frontend \
  --build-arg NEXT_PUBLIC_API_URL=https://nexus.yourdomain.com/api
docker tag nexus-frontend:v1.0.0 ${ECR_FRONTEND}:v1.0.0
docker push ${ECR_FRONTEND}:v1.0.0
```

### F. Deploy to Kubernetes

```bash
# Update image references in manifests
sed -i "s|YOUR_REGISTRY/nexus-backend:latest|${ECR_BACKEND}:v1.0.0|g" \
  infra/k8s/backend/deployment.yaml
sed -i "s|YOUR_REGISTRY/nexus-frontend:latest|${ECR_FRONTEND}:v1.0.0|g" \
  infra/k8s/frontend/deployment.yaml

# Deploy namespace and RBAC
kubectl apply -f infra/k8s/namespace.yaml

# Deploy secrets (use External Secrets Operator in production)
# ESO syncs from AWS Secrets Manager automatically.
# Manual fallback:
kubectl create secret generic nexus-secrets \
  --namespace nexus \
  --from-literal=OPENAI_API_KEY="${TF_VAR_openai_api_key}" \
  --from-literal=LANGFUSE_PUBLIC_KEY="${TF_VAR_langfuse_public_key}" \
  --from-literal=LANGFUSE_SECRET_KEY="${TF_VAR_langfuse_secret_key}" \
  --from-literal=REDIS_PASSWORD="${TF_VAR_redis_auth_token}"

kubectl apply -f infra/k8s/configmap.yaml

# Deploy services
kubectl apply -f infra/k8s/chromadb/statefulset.yaml
kubectl apply -f infra/k8s/redis/statefulset.yaml
kubectl apply -f infra/k8s/backend/deployment.yaml
kubectl apply -f infra/k8s/backend/service.yaml
kubectl apply -f infra/k8s/backend/hpa.yaml
kubectl apply -f infra/k8s/frontend/deployment.yaml
kubectl apply -f infra/k8s/frontend/service.yaml
kubectl apply -f infra/k8s/frontend/hpa.yaml

# cert-manager for TLS
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set installCRDs=true

kubectl apply -f infra/k8s/ingress.yaml

# Wait for all pods
kubectl rollout status deployment/nexus-backend -n nexus
kubectl rollout status deployment/nexus-frontend -n nexus
```

### G. Deploy Monitoring Stack

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  -f infra/k8s/monitoring/prometheus-values.yaml

# Enable Container Insights (CloudWatch)
aws eks create-addon \
  --cluster-name nexus-production \
  --addon-name amazon-cloudwatch-observability \
  --region us-east-1
```

### H. Configure Route 53

```bash
# Get the ingress ALB hostname
ALB_HOSTNAME=$(kubectl get ingress nexus-ingress -n nexus \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Create Route 53 alias record
aws route53 change-resource-record-sets \
  --hosted-zone-id $(terraform -chdir=infra/aws output -raw route53_zone_id) \
  --change-batch "{
    \"Changes\":[{
      \"Action\":\"CREATE\",
      \"ResourceRecordSet\":{
        \"Name\":\"nexus.yourdomain.com\",
        \"Type\":\"A\",
        \"AliasTarget\":{
          \"DNSName\":\"${ALB_HOSTNAME}\",
          \"EvaluateTargetHealth\":true,
          \"HostedZoneId\":\"Z35SXDOTRQ7X7K\"
        }
      }
    }]
  }"
```

### I. Verify

```bash
kubectl get pods -n nexus
kubectl get hpa -n nexus
curl -f https://nexus.yourdomain.com/health
curl -f https://nexus.yourdomain.com/ready
```

---

## 2. GCP — GKE Deployment

### A. Bootstrap

```bash
# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Create Terraform state bucket
gsutil mb -l us-central1 gs://nexus-terraform-state-gcp
gsutil versioning set on gs://nexus-terraform-state-gcp

# Enable billing (required for GKE)
gcloud beta billing projects link YOUR_PROJECT_ID \
  --billing-account YOUR_BILLING_ACCOUNT_ID
```

### B. Provision Infrastructure

```bash
cd infra/gcp

export TF_VAR_project_id="your-gcp-project-id"
export TF_VAR_openai_api_key="sk-..."
export TF_VAR_langfuse_public_key="pk-lf-..."
export TF_VAR_langfuse_secret_key="sk-lf-..."
export TF_VAR_domain_name="nexus.yourdomain.com"

terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### C. Configure kubectl

```bash
gcloud container clusters get-credentials nexus-production \
  --region us-central1 \
  --project YOUR_PROJECT_ID

kubectl get nodes
```

### D. Build and Push Images

```bash
REGISTRY=$(terraform -chdir=infra/gcp output -raw artifact_registry_url)
gcloud auth configure-docker us-central1-docker.pkg.dev

docker build -t nexus-backend:v1.0.0 ./backend
docker tag nexus-backend:v1.0.0 ${REGISTRY}/backend:v1.0.0
docker push ${REGISTRY}/backend:v1.0.0

docker build -t nexus-frontend:v1.0.0 ./frontend \
  --build-arg NEXT_PUBLIC_API_URL=https://nexus.yourdomain.com/api
docker tag nexus-frontend:v1.0.0 ${REGISTRY}/frontend:v1.0.0
docker push ${REGISTRY}/frontend:v1.0.0
```

### E. Deploy to Kubernetes

```bash
# Update image refs
sed -i "s|YOUR_REGISTRY/nexus-backend:latest|${REGISTRY}/backend:v1.0.0|g" \
  infra/k8s/backend/deployment.yaml
sed -i "s|YOUR_REGISTRY/nexus-frontend:latest|${REGISTRY}/frontend:v1.0.0|g" \
  infra/k8s/frontend/deployment.yaml

# For GCP, use filestore-rwx StorageClass for CAD output
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gcp-filestore
provisioner: filestore.csi.storage.gke.io
volumeBindingMode: Immediate
allowVolumeExpansion: true
parameters:
  tier: standard
  network: nexus-vpc
EOF

# Replace efs-sc with gcp-filestore in backend/deployment.yaml
sed -i "s|efs-sc|gcp-filestore|g" infra/k8s/backend/deployment.yaml

kubectl apply -f infra/k8s/namespace.yaml

# Secrets via GCP Secret Manager + External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  -n external-secrets --create-namespace

# Or manual:
kubectl create secret generic nexus-secrets --namespace nexus \
  --from-literal=OPENAI_API_KEY="${TF_VAR_openai_api_key}" \
  --from-literal=LANGFUSE_PUBLIC_KEY="${TF_VAR_langfuse_public_key}" \
  --from-literal=LANGFUSE_SECRET_KEY="${TF_VAR_langfuse_secret_key}" \
  --from-literal=REDIS_PASSWORD="$(openssl rand -base64 32)"

kubectl apply -f infra/k8s/configmap.yaml
kubectl apply -f infra/k8s/chromadb/statefulset.yaml
kubectl apply -f infra/k8s/redis/statefulset.yaml
kubectl apply -f infra/k8s/backend/
kubectl apply -f infra/k8s/frontend/

# cert-manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace --set installCRDs=true

# Update ingress to use GKE ingress class
sed -i "s|kubernetes.io/ingress.class: \"nginx\"|kubernetes.io/ingress.class: \"gce\"|g" \
  infra/k8s/ingress.yaml
kubectl apply -f infra/k8s/ingress.yaml
```

### F. Deploy Monitoring

```bash
# Prometheus + Grafana
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  -f infra/k8s/monitoring/prometheus-values.yaml

# Cloud Monitoring integration is automatic for GKE
# Enable managed Prometheus (optional, replaces self-hosted Prometheus):
gcloud container clusters update nexus-production \
  --enable-managed-prometheus \
  --region us-central1
```

### G. Configure Cloud DNS

```bash
# Get ingress IP
INGRESS_IP=$(kubectl get ingress nexus-ingress -n nexus \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Add A record to Cloud DNS
gcloud dns record-sets create nexus.yourdomain.com \
  --zone=nexus-zone \
  --type=A \
  --ttl=300 \
  --rrdatas=${INGRESS_IP}
```

### H. Verify

```bash
kubectl get pods -n nexus
curl -f https://nexus.yourdomain.com/health
```

---

## 3. Azure — AKS Deployment

### A. Bootstrap Terraform State

```bash
# Login
az login
az account set --subscription YOUR_SUBSCRIPTION_ID

# Create state storage
az group create -n nexus-terraform-state-rg -l eastus

az storage account create \
  --name nexustfstate \
  --resource-group nexus-terraform-state-rg \
  --sku Standard_ZRS \
  --encryption-services blob

az storage container create \
  --name tfstate \
  --account-name nexustfstate
```

### B. Provision Infrastructure

```bash
cd infra/azure

export TF_VAR_openai_api_key="sk-..."
export TF_VAR_langfuse_public_key="pk-lf-..."
export TF_VAR_langfuse_secret_key="sk-lf-..."
export TF_VAR_domain_name="nexus.yourdomain.com"
export TF_VAR_alert_email="devops@yourdomain.com"

terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### C. Configure kubectl

```bash
az aks get-credentials \
  --resource-group nexus-production-rg \
  --name nexus-production \
  --overwrite-existing

kubectl get nodes
```

### D. Build and Push Images

```bash
ACR=$(terraform -chdir=infra/azure output -raw acr_login_server)
az acr login --name ${ACR%%.*}

docker build -t nexus-backend:v1.0.0 ./backend
docker tag nexus-backend:v1.0.0 ${ACR}/nexus/backend:v1.0.0
docker push ${ACR}/nexus/backend:v1.0.0

docker build -t nexus-frontend:v1.0.0 ./frontend \
  --build-arg NEXT_PUBLIC_API_URL=https://nexus.yourdomain.com/api
docker tag nexus-frontend:v1.0.0 ${ACR}/nexus/frontend:v1.0.0
docker push ${ACR}/nexus/frontend:v1.0.0
```

### E. Deploy to Kubernetes

```bash
# Update image refs
sed -i "s|YOUR_REGISTRY/nexus-backend:latest|${ACR}/nexus/backend:v1.0.0|g" \
  infra/k8s/backend/deployment.yaml
sed -i "s|YOUR_REGISTRY/nexus-frontend:latest|${ACR}/nexus/frontend:v1.0.0|g" \
  infra/k8s/frontend/deployment.yaml

# Azure Files StorageClass for RWX
STORAGE_ACCT=$(terraform -chdir=infra/azure output -raw storage_account_name)
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: azurefile-csi
provisioner: file.csi.azure.com
parameters:
  storageAccount: ${STORAGE_ACCT}
  skuName: Standard_ZRS
mountOptions:
  - dir_mode=0777
  - file_mode=0777
  - uid=1001
  - gid=1001
volumeBindingMode: Immediate
allowVolumeExpansion: true
EOF

sed -i "s|efs-sc|azurefile-csi|g" infra/k8s/backend/deployment.yaml

kubectl apply -f infra/k8s/namespace.yaml

# Secrets from Azure Key Vault via AKS Secrets Store CSI Driver
kubectl apply -f - <<EOF
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: nexus-kv-secrets
  namespace: nexus
spec:
  provider: azure
  secretObjects:
    - secretName: nexus-secrets
      type: Opaque
      data:
        - objectName: openai-api-key
          key: OPENAI_API_KEY
        - objectName: langfuse-secret-key
          key: LANGFUSE_SECRET_KEY
        - objectName: langfuse-public-key
          key: LANGFUSE_PUBLIC_KEY
  parameters:
    usePodIdentity: "false"
    useVMManagedIdentity: "true"
    userAssignedIdentityID: ""
    keyvaultName: $(terraform -chdir=infra/azure output -raw key_vault_name)
    tenantId: $(az account show --query tenantId -o tsv)
    objects: |
      array:
        - |
          objectName: openai-api-key
          objectType: secret
        - |
          objectName: langfuse-secret-key
          objectType: secret
        - |
          objectName: langfuse-public-key
          objectType: secret
EOF

kubectl apply -f infra/k8s/configmap.yaml
kubectl apply -f infra/k8s/chromadb/statefulset.yaml
kubectl apply -f infra/k8s/redis/statefulset.yaml
kubectl apply -f infra/k8s/backend/
kubectl apply -f infra/k8s/frontend/

# AGIC (Application Gateway Ingress Controller)
helm repo add application-gateway-kubernetes-ingress \
  https://appgwingress.blob.core.windows.net/ingress-azure-helm-package/

# Update ingress class for Azure Application Gateway
sed -i "s|kubernetes.io/ingress.class: \"nginx\"|kubernetes.io/ingress.class: \"azure/application-gateway\"|g" \
  infra/k8s/ingress.yaml
kubectl apply -f infra/k8s/ingress.yaml
```

### F. Deploy Monitoring

```bash
# Prometheus + Grafana (same as other clouds)
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  -f infra/k8s/monitoring/prometheus-values.yaml

# Azure Monitor Container Insights is already enabled via Terraform (oms_agent block)
# View in: Azure Portal → AKS cluster → Insights
```

### G. Configure Azure DNS

```bash
APPGW_IP=$(terraform -chdir=infra/azure output -raw appgw_public_ip)

az network dns record-set a add-record \
  --resource-group nexus-production-rg \
  --zone-name nexus.yourdomain.com \
  --record-set-name "@" \
  --ipv4-address ${APPGW_IP}
```

### H. Verify

```bash
kubectl get pods -n nexus
kubectl get hpa -n nexus
curl -f https://nexus.yourdomain.com/health
```

---

## 4. Monitoring & Observability

### Access Grafana

```bash
# Port-forward (before DNS is live)
kubectl port-forward svc/prometheus-grafana -n monitoring 3000:80

# URL: http://localhost:3000
# Default credentials: admin / REPLACE_WITH_SECURE_PASSWORD (set in prometheus-values.yaml)
```

### Access Prometheus

```bash
kubectl port-forward svc/prometheus-kube-prometheus-prometheus -n monitoring 9090:9090
```

### Langfuse — LLM Tracing

The NEXUS backend sends all LLM spans to Langfuse automatically (configured via `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY`).
- View traces: https://cloud.langfuse.com
- Filter by `app: nexus` tag
- Every pipeline run creates a root span with 6 child agent spans

### Key Dashboards to Import in Grafana

| Dashboard | Grafana ID | Purpose |
|-----------|-----------|---------|
| Kubernetes Cluster Overview | 7249 | Node CPU/mem/pod status |
| FastAPI Metrics | 14282 | API latency, RPS, error rate |
| Redis Dashboard | 763 | Hit rate, connections, memory |
| NGINX Ingress | 9614 | Ingress traffic and errors |

---

## 5. CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml  (create this file separately)
name: Deploy NEXUS
on:
  push:
    branches: [master]
    tags: ['v*']

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Login to ECR
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push images
        run: |
          VERSION=${GITHUB_REF_NAME}
          docker build -t ${{ secrets.ECR_BACKEND }}:${VERSION} ./backend
          docker push ${{ secrets.ECR_BACKEND }}:${VERSION}
          docker build -t ${{ secrets.ECR_FRONTEND }}:${VERSION} ./frontend \
            --build-arg NEXT_PUBLIC_API_URL=${{ secrets.API_URL }}
          docker push ${{ secrets.ECR_FRONTEND }}:${VERSION}

      - name: Deploy to EKS
        run: |
          aws eks update-kubeconfig --name nexus-production --region us-east-1
          kubectl set image deployment/nexus-backend \
            backend=${{ secrets.ECR_BACKEND }}:${GITHUB_REF_NAME} -n nexus
          kubectl set image deployment/nexus-frontend \
            frontend=${{ secrets.ECR_FRONTEND }}:${GITHUB_REF_NAME} -n nexus
          kubectl rollout status deployment/nexus-backend -n nexus --timeout=5m
          kubectl rollout status deployment/nexus-frontend -n nexus --timeout=5m
```

---

## 6. Disaster Recovery

| Component | Strategy | RTO | RPO |
|-----------|----------|-----|-----|
| EKS/GKE/AKS | Multi-AZ node groups + PDB | < 5 min | 0 |
| Redis | Managed HA (ElastiCache/Memorystore/Azure Cache) | < 1 min | < 60s |
| ChromaDB | StatefulSet + PVC snapshots (nightly) | < 15 min | 24h |
| CAD output | S3/GCS/Blob with versioning | < 1 min | 0 |
| Secrets | Secrets Manager (multi-region replica) | < 1 min | 0 |

```bash
# Snapshot ChromaDB volume (AWS example)
VOLUME_ID=$(kubectl get pv -n nexus -o jsonpath='{.items[?(@.spec.claimRef.name=="chroma-data-nexus-chromadb-0")].spec.awsElasticBlockStore.volumeID}')
aws ec2 create-snapshot --volume-id ${VOLUME_ID} --description "nexus-chromadb-$(date +%Y%m%d)"
```

---

## 7. Security Hardening Checklist

- [ ] Restrict `allowed_cidr_blocks` / `allowed_ip_ranges` to VPN/office IPs only
- [ ] Enable WAF rules (AWS WAFv2 / Azure App Gateway WAF / Cloud Armor)
- [ ] Rotate all secrets in Secrets Manager/Key Vault every 90 days
- [ ] Enable Kubernetes audit logging
- [ ] Apply Kubernetes PodSecurityStandard `restricted` policy
- [ ] Scan images in ECR/ACR/Artifact Registry on every push (already configured)
- [ ] Enable GuardDuty (AWS) / Security Command Center (GCP) / Defender for Cloud (Azure)
- [ ] Network policies enforced (namespace.yaml already includes default-deny)
- [ ] TLS 1.3 enforced on all ingress
- [ ] Enable VPC Flow Logs for network audit trail

---

## 8. Cost Estimates (Monthly, Production)

| Service | AWS | GCP | Azure |
|---------|-----|-----|-------|
| Kubernetes (3 nodes m6i.xlarge) | ~$450 | ~$420 (Autopilot, pay-per-pod) | ~$480 |
| Spot/pipeline nodes (avg 2 active) | ~$60 | ~$50 | ~$65 |
| Managed Redis (r7g.medium/2GB HA) | ~$130 | ~$80 | ~$140 |
| Storage (50GB + CAD) | ~$15 | ~$10 | ~$15 |
| Load Balancer | ~$20 | ~$18 | ~$35 (AppGW) |
| DNS | ~$1 | ~$1 | ~$1 |
| Monitoring (Container Insights) | ~$20 | ~$10 | ~$15 |
| **Total estimate** | **~$700/mo** | **~$590/mo** | **~$750/mo** |

> Spot instances on AWS can reduce pipeline node costs by 60–80%.
> GCP Autopilot is cheapest for variable workloads — you pay per pod, not per node.
