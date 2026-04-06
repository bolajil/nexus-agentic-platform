#!/bin/bash
# ── Azure Container Apps Deployment ──────────────────────────────────────────
# Prerequisites:
#   - Azure CLI installed and logged in (az login)
#   - Docker installed
#
# Secrets Setup (run once):
#   az keyvault secret set --vault-name nexus-kv --name openai-api-key --value "sk-xxx"
#   az keyvault secret set --vault-name nexus-kv --name zoo-api-key --value "xxx"

set -e

# Configuration
RESOURCE_GROUP="nexus-rg"
LOCATION="eastus"
ACR_NAME="nexusacr"
CONTAINER_APP_NAME="nexus-backend"
CONTAINER_APP_ENV="nexus-env"
KEY_VAULT_NAME="nexus-kv"

echo "🚀 Deploying NEXUS Platform to Azure Container Apps"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   Location: $LOCATION"

# 1. Create resource group (if needed)
az group create --name $RESOURCE_GROUP --location $LOCATION 2>/dev/null || true

# 2. Create ACR (if needed)
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic 2>/dev/null || true

# 3. Login to ACR
echo "📦 Logging into Azure Container Registry..."
az acr login --name $ACR_NAME

# 4. Build and push image
echo "🔨 Building and pushing Docker image..."
az acr build --registry $ACR_NAME --image nexus-backend:latest ./backend

# 5. Create Container Apps environment (if needed)
az containerapp env create \
  --name $CONTAINER_APP_ENV \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION 2>/dev/null || true

# 6. Get secrets from Key Vault
OPENAI_KEY=$(az keyvault secret show --vault-name $KEY_VAULT_NAME --name openai-api-key --query value -o tsv)
ZOO_KEY=$(az keyvault secret show --vault-name $KEY_VAULT_NAME --name zoo-api-key --query value -o tsv 2>/dev/null || echo "")

# 7. Deploy Container App
echo "🚀 Deploying Container App..."
az containerapp create \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_APP_ENV \
  --image $ACR_NAME.azurecr.io/nexus-backend:latest \
  --target-port 8003 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 0.5 \
  --memory 1.0Gi \
  --secrets openai-key="$OPENAI_KEY" zoo-key="$ZOO_KEY" \
  --env-vars \
    ENVIRONMENT=production \
    LOG_LEVEL=INFO \
    OPENAI_API_KEY=secretref:openai-key \
    ZOO_API_KEY=secretref:zoo-key \
  --registry-server $ACR_NAME.azurecr.io

# 8. Get URL
FQDN=$(az containerapp show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)
echo "✅ Deployment complete!"
echo "   URL: https://$FQDN"
echo "   Health: https://$FQDN/health"
