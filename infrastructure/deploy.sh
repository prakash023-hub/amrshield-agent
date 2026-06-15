#!/bin/bash
# AMRShield - Cloud Run Deployment Script

PROJECT_ID="project-d52ffa3b-95bb-4dfb-af0"
REGION="us-central1"
SERVICE_NAME="amrshield"

echo "🚀 Deploying AMRShield to Cloud Run..."

# Build from source (Artifact Registry — avoids legacy gcr.io push issues)
gcloud run deploy $SERVICE_NAME \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars GCP_PROJECT_ID=$PROJECT_ID,GCP_LOCATION=$REGION,PHARMAGUARD_EDGE_NODE=edge-india-south-01 \
  --project $PROJECT_ID

echo "✅ Deployed! Getting URL..."
gcloud run services describe $SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --format 'value(status.url)'
