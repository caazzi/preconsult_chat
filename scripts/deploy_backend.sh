#!/bin/bash

# --- CONFIGURATION (UPDATE THESE) ---
# --- CONFIGURATION (OVERRIDABLE VIA ENV) ---
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"securemed-chat-494521"} 
REGION=${GOOGLE_CLOUD_REGION:-"us-central1"}
SERVICE_NAME=${SERVICE_NAME:-"preconsult"}
# ------------------------------------

PROFILE=${1:-${DEPLOY_PROFILE:-"cost_optimized"}}
echo "🚀 Starting Backend Deployment for PreConsult (Profile: $PROFILE)..."

# Check if logged in
if ! gcloud auth list --format="value(account)" | grep -q "@"; then
    echo "❌ Error: Not logged into gcloud. Please run 'gcloud auth login' first."
    exit 1
fi

# Set the active project
gcloud config set project $PROJECT_ID

if [ -z "$PRECONSULT_API_KEY" ]; then
    echo "❌ Error: PRECONSULT_API_KEY environment variable is not set."
    echo "   Set it before running this script: export PRECONSULT_API_KEY=<your-secret-key>"
    exit 1
fi

if [ "$PROFILE" = "high_performance" ]; then
    PROFILE_FLAGS="--min-instances 2 --max-instances 10 --concurrency 40 --cpu 2 --memory 2Gi --no-cpu-throttling"
else
    PROFILE_FLAGS="--min-instances 1 --max-instances 5 --concurrency 80 --cpu 1 --memory 1Gi --cpu-throttling"
fi

echo "🐳 Building and deploying container to Cloud Run ($PROFILE)..."
gcloud run deploy $SERVICE_NAME \
    --source . \
    --platform managed \
    --region $REGION \
    $PROFILE_FLAGS \
    --timeout 300s \
    --use-http2 \
    --allow-unauthenticated \
    --set-env-vars="PRECONSULT_API_KEY=$PRECONSULT_API_KEY,VERTEX_AI_REGION=us-central1"

echo "✅ Backend Deployment Finished!"
echo "🔗 Your API URL should be visible above."
echo "👉 Next: Update your Reflex Frontend with the new API URL."
