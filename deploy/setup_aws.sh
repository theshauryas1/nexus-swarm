#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  NexusSwarm — AWS Provisioning & Bootstrapping Script
#  Run this script locally to provision your AWS cloud infrastructure.
# ═══════════════════════════════════════════════════════════════

set -e

# Configuration
REGION="us-east-1"
DB_NAME="nexusswarm"
DB_USER="postgres"
DB_INSTANCE_ID="nexusswarm-db"
BACKEND_REPO="nexusswarm-backend"
FRONTEND_REPO="nexusswarm-frontend"

echo "🤖 Starting AWS provisioning script for NexusSwarm..."

# 1. Verify AWS CLI configuration and retrieve Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
if [ -z "$ACCOUNT_ID" ]; then
    echo "❌ ERROR: No active AWS credentials configured. Run 'aws configure' first."
    exit 1
fi
echo "✅ Active AWS Account: $ACCOUNT_ID"
echo "✅ Target Region: $REGION"

BUCKET_NAME="nexusswarm-outputs-${ACCOUNT_ID}-${REGION}"

# 2. Create Amazon ECR Repositories
echo "🐳 Creating Amazon ECR Docker repositories..."
aws ecr create-repository --repository-name "$BACKEND_REPO" --region "$REGION" || echo "⚠️ Repository $BACKEND_REPO already exists, skipping..."
aws ecr create-repository --repository-name "$FRONTEND_REPO" --region "$REGION" || echo "⚠️ Repository $FRONTEND_REPO already exists, skipping..."

# 3. Create Amazon S3 Bucket for persistent agent outputs
echo "🗂️ Creating S3 Bucket: $BUCKET_NAME..."
if [ "$REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION" || echo "⚠️ Bucket already exists, skipping..."
else
    aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION" \
        --create-bucket-configuration LocationConstraint="$REGION" || echo "⚠️ Bucket already exists, skipping..."
fi

# 4. Create Secrets in Secrets Manager
echo "🔑 Enter database master password for '$DB_USER':"
read -sp "Password: " DB_PASS
echo ""

echo "🔑 Enter your NVIDIA API Key:"
read -sp "API Key: " NVIDIA_KEY
echo ""

echo "🔒 Storing secrets in AWS Secrets Manager..."
aws secretsmanager create-secret --name nexusswarm/nvidia-key \
    --secret-string "$NVIDIA_KEY" --region "$REGION" || \
aws secretsmanager put-secret-value --secret-id nexusswarm/nvidia-key \
    --secret-string "$NVIDIA_KEY" --region "$REGION"

aws secretsmanager create-secret --name nexusswarm/db-pass \
    --secret-string "$DB_PASS" --region "$REGION" || \
aws secretsmanager put-secret-value --secret-id nexusswarm/db-pass \
    --secret-string "$DB_PASS" --region "$REGION"

# 5. Provision RDS PostgreSQL Database Instance (Free Tier Eligible)
echo "🗄️ Creating Amazon RDS PostgreSQL instance (db.t4g.micro, PostgreSQL 15)..."
aws rds create-db-instance \
    --db-instance-identifier "$DB_INSTANCE_ID" \
    --db-instance-class db.t4g.micro \
    --engine postgres \
    --engine-version 15 \
    --master-username "$DB_USER" \
    --master-user-password "$DB_PASS" \
    --allocated-storage 20 \
    --region "$REGION" \
    --publicly-accessible \
    --no-cli-pager || echo "⚠️ RDS instance already exists or is building, skipping..."

# Wait for RDS to be available to describe endpoints
echo "⌛ Querying RDS DB status..."
aws rds wait db-instance-exists --db-instance-identifier "$DB_INSTANCE_ID" --region "$REGION"

# 6. Setup IAM App Runner Roles
echo "👤 Configuring App Runner execution role..."
# Write role trust policy to file
TRUST_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "build.apprunner.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    },
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "tasks.apprunner.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
)

ROLE_NAME="NexusSwarmAppRunnerRole"
aws iam create-role --role-name "$ROLE_NAME" --assume-role-policy-document "$TRUST_POLICY" || echo "⚠️ IAM Role already exists, skipping..."

# Attach ECR and standard policies
aws iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"

# Create Custom Policy for S3 and Secrets Manager Access
POLICY_DOC=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::$BUCKET_NAME",
        "arn:aws:s3:::$BUCKET_NAME/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:$REGION:$ACCOUNT_ID:secret:nexusswarm/*"
      ]
    }
  ]
}
EOF
)

POLICY_ARN=$(aws iam create-policy --policy-name "NexusSwarmAppRunnerPolicy" --policy-document "$POLICY_DOC" --query "Policy.Arn" --output text 2>/dev/null || \
             echo "arn:aws:iam::${ACCOUNT_ID}:policy/NexusSwarmAppRunnerPolicy")

aws iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn "$POLICY_ARN"

echo "🎉 AWS Infrastructure Provisioned successfully!"
echo "----------------------------------------------------"
echo "Next Steps:"
echo "1. Wait for RDS Instance to finish starting up. Run:"
echo "   aws rds describe-db-instances --db-instance-identifier $DB_INSTANCE_ID --region $REGION --query \"DBInstances[0].Endpoint\""
echo "2. Deploy frontend and backend using:"
echo "   bash deploy/deploy_aws.sh"
echo "----------------------------------------------------"
