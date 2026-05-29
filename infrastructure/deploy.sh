#!/bin/bash
# AMRShield - Cloud Run Deployment Script

PROJECT_ID="project-d52ffa3b-95bb-4dfb-af0"
REGION="us-central1"
SERVICE_NAME="amrshield"
IMAGE="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "🚀 Deploying AMRShield to Cloud Run..."

# Build and push image
gcloud builds submit \
  --tag $IMAGE \
  --project $PROJECT_ID \
  -f infrastructure/Dockerfile \
  .

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars GCP_PROJECT_ID=$PROJECT_ID,GCP_LOCATION=$REGION \
  --project $PROJECT_ID

echo "✅ Deployed! Getting URL..."
gcloud run services describe $SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --format 'value(status.url)'
