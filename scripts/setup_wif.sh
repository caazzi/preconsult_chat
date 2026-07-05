#!/bin/bash
set -e

PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"securemed-chat-494521"}
REPO=${GITHUB_REPO:-"caazzi/preconsult_chat"}
SERVICE_ACCOUNT="github-deploy-sa"

echo "Creating Service Account..."
gcloud iam service-accounts create $SERVICE_ACCOUNT \
    --project="${PROJECT_ID}" \
    --display-name="GitHub Actions Deploy SA" || true

echo "Granting roles to Service Account..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# --- Workload Identity Pool Management ---
echo "Handling Workload Identity Pool..."
gcloud iam workload-identity-pools create "github-pool" \
    --project="${PROJECT_ID}" \
    --location="global" \
    --display-name="GitHub Actions Pool" || true

# Robustly fetch the Pool ID
WORKLOAD_IDENTITY_POOL_ID=$(gcloud iam workload-identity-pools describe "github-pool" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --format="value(name)")

if [ -z "$WORKLOAD_IDENTITY_POOL_ID" ]; then
    echo "Error: Failed to fetch Workload Identity Pool ID."
    exit 1
fi

echo "Handling Workload Identity Provider..."
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
    --project="${PROJECT_ID}" \
    --location="global" \
    --workload-identity-pool="github-pool" \
    --display-name="GitHub provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
    --attribute-condition="assertion.repository_owner == 'caazzi'" \
    --issuer-uri="https://token.actions.githubusercontent.com" || true

echo "Allowing GitHub actions from ${REPO} to impersonate the Service Account..."
gcloud iam service-accounts add-iam-policy-binding "${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --project="${PROJECT_ID}" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_POOL_ID}/attribute.repository/${REPO}"

echo "Done."
echo "Pool ID: ${WORKLOAD_IDENTITY_POOL_ID}"
echo "Provider Name: ${WORKLOAD_IDENTITY_POOL_ID}/providers/github-provider"
echo "Service Account: ${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"
