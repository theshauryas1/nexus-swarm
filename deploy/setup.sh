#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  NexusSwarm — Google Cloud Bootstrapping Script
#  Run this script locally to provision your cloud infrastructure.
# ═══════════════════════════════════════════════════════════════

set -e

# Configuration
REGION="us-central1"
INSTANCE_NAME="nexusswarm-db"
DB_NAME="nexusswarm"
DB_USER="postgres"
REPOSITORY_NAME="nexusswarm"

echo "🤖 Starting Google Cloud provision script for NexusSwarm..."

# 1. Retrieve current project ID
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ ERROR: No active gcloud project set. Run 'gcloud config set project <PROJECT_ID>' first."
    exit 1
fi
echo "✅ Active project: $PROJECT_ID"

BUCKET_NAME="nexusswarm-outputs-${PROJECT_ID}"

# 2. Enable Required APIs
echo "📡 Enabling Google Cloud APIs (Run, SQL, Secret Manager, Cloud Build, Artifact Registry)..."
gcloud services enable \
    run.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com

# 3. Create Artifact Registry Repository
echo "🐳 Creating Artifact Registry repository..."
gcloud artifacts repositories create "$REPOSITORY_NAME" \
    --repository-format=docker \
    --location="$REGION" \
    --description="NexusSwarm Docker images" || echo "⚠️ Repository already exists, skipping..."

# 4. Create Google Cloud Storage Bucket
echo "🗂️ Creating Cloud Storage bucket for generated files..."
gcloud storage buckets create "gs://${BUCKET_NAME}" \
    --location="$REGION" || echo "⚠️ Bucket already exists, skipping..."

# 5. Create Cloud SQL PostgreSQL Instance
echo "🔑 Enter database master password for '$DB_USER':"
read -sp "Password: " DB_PASS
echo ""

echo "🛢️ Creating Cloud SQL PostgreSQL instance (db-f1-micro, PostgreSQL 15)..."
gcloud sql instances create "$INSTANCE_NAME" \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region="$REGION" \
    --root-password="$DB_PASS" || echo "⚠️ SQL Instance already exists..."

echo "🛢️ Creating database..."
gcloud sql databases create "$DB_NAME" \
    --instance="$INSTANCE_NAME" || echo "⚠️ Database already exists..."

# 6. Configure Secrets in Secret Manager
echo "🔑 Enter your NVIDIA API Key:"
read -sp "API Key: " NVIDIA_KEY
echo ""

echo "🔒 Creating secret in Secret Manager for NVIDIA API Key..."
gcloud secrets create nexusswarm-nvidia-key --replication-policy="automatic" || echo "⚠️ Secret already exists..."
echo -n "$NVIDIA_KEY" | gcloud secrets versions add nexusswarm-nvidia-key --data-file=-

echo "🔒 Creating database password secret..."
gcloud secrets create nexusswarm-db-pass --replication-policy="automatic" || echo "⚠️ Secret already exists..."
echo -n "$DB_PASS" | gcloud secrets versions add nexusswarm-db-pass --data-file=-

# 7. Configure IAM Roles for Cloud Run Service Account
echo "👤 Granting permissions to the Cloud Run service account..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
RUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant Secret Manager Access
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${RUN_SA}" \
    --role="roles/secretmanager.secretAccessor"

# Grant Cloud SQL Access
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${RUN_SA}" \
    --role="roles/cloudsql.client"

# Grant Storage Admin for GCS bucket
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
    --member="serviceAccount:${RUN_SA}" \
    --role="roles/storage.admin"

CONNECTION_NAME=$(gcloud sql instances describe "$INSTANCE_NAME" --format="value(connectionName)")

echo "🎉 GCP Infrastructure Provisioned successfully!"
echo "----------------------------------------------------"
echo "Next Steps:"
echo "1. Run the following command to deploy using Cloud Build:"
echo "   gcloud builds submit --config=deploy/cloudbuild.yaml --substitutions=_DB_CONNECTION=\"$CONNECTION_NAME\",_GCS_BUCKET=\"$BUCKET_NAME\""
echo "----------------------------------------------------"