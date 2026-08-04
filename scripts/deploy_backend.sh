#!/bin/bash
#
# PreConsult Cloud Run deployment helper.
#
# IMPORTANT: The canonical build+deploy pipeline is the GitHub Actions CI/CD
# workflow (`.github/workflows/ci-cd.yml`), which builds the container with
# `docker buildx` into the `securemed-repo` Artifact Registry repo and deploys
# with `google-github-actions/deploy-cloudrun`. Images produced that way are the
# only ones verified to serve correctly.
#
# This script deploys an ALREADY-BUILT image from that registry — it does NOT
# rebuild from `--source` (which has produced unservable `cloud-run-source-deploy`
# images that return 502 protocol errors). Prefer running the workflow dispatch
# of `ci-cd.yml` over this script whenever possible.
#
# Usage:
#   scripts/deploy_backend.sh [cost_optimized|high_performance] [IMAGE_REF]
#
#   IMAGE_REF  Optional image tag/digest. Defaults to the latest `latest` tag
#              in $AR_REPO.

set -euo pipefail

# --- Configuration (overridable via env) ---
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"securemed-chat-494521"}
REGION=${GOOGLE_CLOUD_REGION:-"us-central1"}
SERVICE_NAME=${SERVICE_NAME:-"preconsult"}
AR_REPO=${AR_REPO:-"securemed-repo"}
# -------------------------------------------------

PROFILE=${1:-${DEPLOY_PROFILE:-"cost_optimized"}}
IMAGE_REF=${2:-"$REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/$SERVICE_NAME:latest"}

echo "🚀 Starting Cloud Run deployment for PreConsult (Profile: $PROFILE)"
echo "   image: $IMAGE_REF"

# Check if logged in
if ! gcloud auth list --format="value(account)" | grep -q "@"; then
    echo "❌ Error: Not logged into gcloud. Please run 'gcloud auth login' first."
    exit 1
fi

gcloud config set project "$PROJECT_ID"

# Secrets are injected from Secret Manager (NOT plaintext) to match the existing
# live config and keep the API key out of logs/command line.
API_KEY_SECRET=${API_KEY_SECRET:-"SECUREMED_API_KEY"}
REDIS_URL_SECRET=${REDIS_URL_SECRET:-"REDIS_URL"}
SECRET_VERSION=${SECRET_VERSION:-"latest"}

for s in "$API_KEY_SECRET" "$REDIS_URL_SECRET"; do
    if ! gcloud secrets list --project="$PROJECT_ID" --format="value(name)" 2>/dev/null | grep -qx "$s"; then
        echo "❌ Error: SecretManager secret '$s' not found in project $PROJECT_ID."
        exit 1
    fi
done

# Check the image is actually present in the registry (fail fast on typos).
if ! gcloud artifacts docker images describe "$IMAGE_REF" --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "❌ Error: image '$IMAGE_REF' not found. Build+push via the CI/CD workflow first."
    echo "   Or run the 'Deploy to Cloud Run' workflow_dispatch in GitHub Actions."
    exit 1
fi

if [ "$PROFILE" = "high_performance" ]; then
    PROFILE_FLAGS="--min-instances 2 --max-instances 10 --concurrency 40 --cpu 2 --memory 2Gi --no-cpu-throttling"
else
    # 2Gi guards against worker SIGABRT/OOM during streaming LLM/PDF sessions
    # (2 Uvicorn workers x 4 threads compete for the 1Gi budget otherwise).
    PROFILE_FLAGS="--min-instances 1 --max-instances 5 --concurrency 60 --cpu 1 --memory 2Gi --cpu-throttling"
fi

echo "🐳 Deploying image to Cloud Run ($SERVICE_NAME in $PROJECT_ID)..."
gcloud run deploy "$SERVICE_NAME" \
    --image="$IMAGE_REF" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --session-affinity \
    $PROFILE_FLAGS \
    --timeout 300s \
    --set-env-vars="API_BASE_URL=https://pre-consult.org,VERTEX_AI_REGION=us-central1,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},LLM_MODEL=gemini-2.5-flash" \
    --update-secrets="PRECONSULT_API_KEY=${API_KEY_SECRET}:${SECRET_VERSION},REDIS_URL=${REDIS_URL_SECRET}:${SECRET_VERSION}"

echo "✅ Backend Deployment Finished!"
echo "🔗 Service URL: https://preconsult-tcjbweemnq-uc.a.run.app"
echo "ℹ️ Note: deploy changes only take effect if the image was built by the CI/CD pipeline."
