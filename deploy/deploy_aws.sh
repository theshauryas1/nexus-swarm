#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  NexusSwarm — AWS Deployment Orchestration Script
#  Run this script to deploy backend and frontend containers to AWS App Runner.
# ═══════════════════════════════════════════════════════════════

set -e

REGION="us-east-1"
BACKEND_SERVICE_NAME="nexusswarm-backend"
FRONTEND_SERVICE_NAME="nexusswarm-frontend"
ROLE_NAME="NexusSwarmAppRunnerRole"
DB_INSTANCE_ID="nexusswarm-db"

echo "🤖 Starting AWS Deployment for NexusSwarm..."

# 1. Retrieve account info
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
ACCESS_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
BUCKET_NAME="nexusswarm-outputs-${ACCOUNT_ID}-${REGION}"

# Login to ECR
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# 2. Get RDS Database Endpoint Host
echo "🗄️ Querying database endpoint..."
RDS_HOST=$(aws rds describe-db-instances --db-instance-identifier "$DB_INSTANCE_ID" --region "$REGION" --query "DBInstances[0].Endpoint.Address" --output text)
if [ "$RDS_HOST" = "None" ] || [ -z "$RDS_HOST" ]; then
    echo "❌ ERROR: RDS Instance is not ready yet. Please wait a minute and rerun."
    exit 1
fi
echo "✅ Database Host: $RDS_HOST"

# 3. Retrieve DB password and store the full database URL as a runtime secret
DB_PASS=$(aws secretsmanager get-secret-value --secret-id nexusswarm/db-pass --region "$REGION" --query "SecretString" --output text)

DATABASE_URL="postgresql+asyncpg://postgres:${DB_PASS}@${RDS_HOST}:5432/nexusswarm"
aws secretsmanager create-secret --name nexusswarm/database-url \
    --secret-string "$DATABASE_URL" --region "$REGION" || \
aws secretsmanager put-secret-value --secret-id nexusswarm/database-url \
    --secret-string "$DATABASE_URL" --region "$REGION"

# 4. Build and Push Backend Image
echo "🐳 Building backend image..."
docker build -t nexusswarm-backend ./backend
BACKEND_ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/nexusswarm-backend:latest"
docker tag nexusswarm-backend:latest "$BACKEND_ECR_URI"

echo "🚀 Pushing backend image to ECR..."
docker push "$BACKEND_ECR_URI"

# 5. Create or Update Backend App Runner Service
echo "📡 Deploying backend service to AWS App Runner..."
BACKEND_SECRET_NVIDIA="arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:nexusswarm/nvidia-key"
BACKEND_SECRET_DATABASE_URL="arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:nexusswarm/database-url"

# Check if Backend Service exists
SERVICE_ARN=$(aws apprunner list-services --region "$REGION" --query "ServiceSummaryList[?ServiceName=='$BACKEND_SERVICE_NAME'].ServiceArn" --output text)

SOURCE_CONFIG=$(cat <<EOF
{
  "ImageRepository": {
    "ImageIdentifier": "$BACKEND_ECR_URI",
    "ImageRepositoryType": "ECR",
    "ImageConfiguration": {
      "Port": "8000",
      "RuntimeEnvironmentVariables": [
        {"Name": "APP_ENV", "Value": "production"},
        {"Name": "S3_BUCKET", "Value": "$BUCKET_NAME"},
        {"Name": "AWS_REGION", "Value": "$REGION"}
      ],
      "RuntimeEnvironmentSecrets": [
        {"Name": "NVIDIA_API_KEY", "Value": "$BACKEND_SECRET_NVIDIA"},
        {"Name": "DATABASE_URL", "Value": "$BACKEND_SECRET_DATABASE_URL"}
      ]
    }
  },
  "AutoDeploymentsEnabled": false,
  "AuthenticationConfiguration": {
    "AccessRoleArn": "$ACCESS_ROLE_ARN"
  }
}
EOF
)

if [ -z "$SERVICE_ARN" ]; then
    echo "➕ Service does not exist. Creating new App Runner Service for backend..."
    SERVICE_ARN=$(aws apprunner create-service \
        --service-name "$BACKEND_SERVICE_NAME" \
        --source-configuration "$SOURCE_CONFIG" \
        --region "$REGION" \
        --query "Service.ServiceArn" \
        --output text)
    echo "✅ App Runner Backend Service created: $SERVICE_ARN"
else
    echo "🔄 Updating existing Backend App Runner Service..."
    aws apprunner update-service \
        --service-arn "$SERVICE_ARN" \
        --source-configuration "$SOURCE_CONFIG" \
        --region "$REGION" \
        --no-cli-pager
    echo "✅ Update requested for: $SERVICE_ARN"
fi

# Wait for backend URL
echo "⌛ Fetching backend URL (may take a few moments for service to spin up)..."
while true; do
    BACKEND_STATUS=$(aws apprunner describe-service --service-arn "$SERVICE_ARN" --region "$REGION" --query "Service.Status" --output text)
    echo "Current Status: $BACKEND_STATUS"
    if [ "$BACKEND_STATUS" = "RUNNING" ]; then
        BACKEND_URL=$(aws apprunner describe-service --service-arn "$SERVICE_ARN" --region "$REGION" --query "Service.ServiceUrl" --output text)
        # Ensure it has http protocol
        BACKEND_URL="https://${BACKEND_URL}"
        break
    elif [ "$BACKEND_STATUS" = "OPERATION_IN_PROGRESS" ]; then
        echo "Waiting..."
        sleep 15
    else
        echo "⚠️ Warning: Service is in state $BACKEND_STATUS. Attempting to fetch URL..."
        BACKEND_URL=$(aws apprunner describe-service --service-arn "$SERVICE_ARN" --region "$REGION" --query "Service.ServiceUrl" --output text)
        BACKEND_URL="https://${BACKEND_URL}"
        break
    fi
done

WS_URL=$(echo "$BACKEND_URL" | sed 's/https/wss/')
echo "✅ Backend API Endpoint: $BACKEND_URL"
echo "✅ WebSocket Endpoint: $WS_URL"

# 6. Output Backend Endpoints and Finish
echo "🎉 Deployment successful!"
echo "----------------------------------------------------"
echo "Backend API Endpoint: $BACKEND_URL"
echo "WebSocket Endpoint:   $WS_URL"
echo "----------------------------------------------------"
