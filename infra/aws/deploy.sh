#!/bin/bash
# ── AWS ECS Fargate Deployment ───────────────────────────────────────────────
# Prerequisites:
#   - AWS CLI configured with appropriate credentials
#   - Docker installed
#   - ECR repository created
#
# Secrets Setup (run once):
#   aws secretsmanager create-secret --name nexus/openai-api-key --secret-string "sk-xxx"
#   aws secretsmanager create-secret --name nexus/zoo-api-key --secret-string "xxx"

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="nexus-backend"
CLUSTER_NAME="nexus-cluster"
SERVICE_NAME="nexus-backend-service"

echo "🚀 Deploying NEXUS Platform to AWS ECS Fargate"
echo "   Region: $AWS_REGION"
echo "   Account: $AWS_ACCOUNT_ID"

# 1. Login to ECR
echo "📦 Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# 2. Build and push Docker image
echo "🔨 Building Docker image..."
docker build -t $ECR_REPO ./backend

echo "📤 Pushing to ECR..."
docker tag $ECR_REPO:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest

# 3. Register task definition
echo "📝 Registering task definition..."
envsubst < infra/aws/task-definition.json > /tmp/task-def.json
aws ecs register-task-definition --cli-input-json file:///tmp/task-def.json

# 4. Update service
echo "🔄 Updating ECS service..."
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --task-definition nexus-platform \
  --force-new-deployment

echo "✅ Deployment initiated! Monitor at:"
echo "   https://$AWS_REGION.console.aws.amazon.com/ecs/home?region=$AWS_REGION#/clusters/$CLUSTER_NAME/services/$SERVICE_NAME"
