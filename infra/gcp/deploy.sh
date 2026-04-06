#!/bin/bash
# ── GCP Cloud Run Deployment ─────────────────────────────────────────────────
# Prerequisites:
#   - gcloud CLI installed and configured
#   - Docker installed
#
# Secrets Setup (run once):
#   echo -n "sk-xxx" | gcloud secrets create openai-api-key --data-file=-
#   echo -n "xxx" | gcloud secrets create zoo-api-key --data-file=-
#   gcloud secrets add-iam-policy-binding openai-api-key \
#     --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
#     --role="roles/secretmanager.secretAccessor"

set -e

# Configuration
PROJECT_ID=$(gcloud config get-value project)
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="nexus-backend"
IMAGE_NAME="gcr.io/$PROJECT_ID/nexus-backend"

echo "🚀 Deploying NEXUS Platform to GCP Cloud Run"
echo "   Project: $PROJECT_ID"
echo "   Region: $REGION"

# 1. Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  containerregistry.googleapis.com \
  secretmanager.googleapis.com

# 2. Build and push image
echo "🔨 Building Docker image with Cloud Build..."
gcloud builds submit --tag $IMAGE_NAME ./backend

# 3. Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --port 8003 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --allow-unauthenticated \
  --set-env-vars "ENVIRONMENT=production,LOG_LEVEL=INFO" \
  --set-secrets "OPENAI_API_KEY=openai-api-key:latest,ZOO_API_KEY=zoo-api-key:latest"

# 4. Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)')
echo "✅ Deployment complete!"
echo "   URL: $SERVICE_URL"
echo "   Health: $SERVICE_URL/health"
