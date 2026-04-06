# NEXUS Platform — Cloud Deployment

Deploy NEXUS to AWS, Azure, or GCP using containers.

## Prerequisites

- Docker installed locally
- Cloud CLI configured (`aws`, `az`, or `gcloud`)
- API keys stored in cloud secrets manager (never in code)

---

## AWS (ECS Fargate)

### 1. Store Secrets in AWS Secrets Manager
```bash
aws secretsmanager create-secret --name nexus/openai-api-key --secret-string "sk-your-key"
aws secretsmanager create-secret --name nexus/zoo-api-key --secret-string "your-zoo-key"
```

### 2. Create ECR Repository
```bash
aws ecr create-repository --repository-name nexus-backend
```

### 3. Create ECS Cluster
```bash
aws ecs create-cluster --cluster-name nexus-cluster
```

### 4. Deploy
```bash
chmod +x infra/aws/deploy.sh
./infra/aws/deploy.sh
```

---

## Azure (Container Apps)

### 1. Store Secrets in Key Vault
```bash
az keyvault create --name nexus-kv --resource-group nexus-rg --location eastus
az keyvault secret set --vault-name nexus-kv --name openai-api-key --value "sk-your-key"
az keyvault secret set --vault-name nexus-kv --name zoo-api-key --value "your-zoo-key"
```

### 2. Deploy
```bash
chmod +x infra/azure/deploy.sh
./infra/azure/deploy.sh
```

---

## GCP (Cloud Run)

### 1. Store Secrets in Secret Manager
```bash
echo -n "sk-your-key" | gcloud secrets create openai-api-key --data-file=-
echo -n "your-zoo-key" | gcloud secrets create zoo-api-key --data-file=-

# Grant access to Cloud Run
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 2. Deploy
```bash
chmod +x infra/gcp/deploy.sh
./infra/gcp/deploy.sh
```

---

## Security Best Practices

| Practice | Implementation |
|----------|----------------|
| **No hardcoded secrets** | All keys in cloud secret managers |
| **Least privilege IAM** | Task roles with minimal permissions |
| **HTTPS only** | All cloud providers enforce TLS |
| **Private networking** | Use VPC/VNet for Redis, ChromaDB |
| **Audit logging** | CloudTrail / Azure Monitor / Cloud Audit |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Load Balancer (HTTPS)                    │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │ Backend  │    │ Backend  │    │ Backend  │
        │ (Fargate/│    │ (Replica │    │ (Replica │
        │ Cloud Run│    │    2)    │    │    N)    │
        └────┬─────┘    └────┬─────┘    └────┬─────┘
             │               │               │
             └───────────────┼───────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
        ┌──────────┐                  ┌──────────┐
        │  Redis   │                  │ ChromaDB │
        │(ElastiCa-│                  │ (Self-   │
        │che/Memor-│                  │ hosted)  │
        │yStore)   │                  │          │
        └──────────┘                  └──────────┘
```

## Cost Estimates (Monthly)

| Provider | Config | Estimated Cost |
|----------|--------|----------------|
| **AWS** | 1 Fargate task (0.5 vCPU, 1GB) + ElastiCache | ~$50-80 |
| **Azure** | Container Apps (0.5 vCPU, 1GB) + Redis Cache | ~$40-70 |
| **GCP** | Cloud Run (min 0, max 3) + Memorystore | ~$30-60 |

*Costs vary by region and usage. Use cloud calculators for precise estimates.*
