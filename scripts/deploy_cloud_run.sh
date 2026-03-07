
#!/usr/bin/env bash
set -euo pipefail
PROJECT_ID=botpproject
REGION=us-central1
SERVICE=rag-service

# Build & deploy via Cloud Build (reproducible)
gcloud builds submit --tag us-central1-docker.pkg.dev/$PROJECT_ID/rag-service/$SERVICE:latest

gcloud run deploy $SERVICE \
  --image us-central1-docker.pkg.dev/$PROJECT_ID/rag-service/$SERVICE:latest \
  --service-account=rag-service@botpproject.iam.gserviceaccount.com \
  --region=$REGION \
  --set-env-vars PROJECT_ID=$PROJECT_ID,REGION=$REGION,VERTEX_LOCATION=$REGION,VERTEX_INDEX_ID=5347067982386298880,VERTEX_INDEX_ENDPOINT=332186652006940672,DEPLOYED_INDEX_ID=rag_chatbot_deployed,MODEL_VARIANT=gemini-2.0-flash-001,REDIS_HOST=10.200.18.59 \
  --allow-unauthenticated

URL=$(gcloud run services describe $SERVICE --region $REGION --format='value(status.url)')
echo "Deployed: $URL"
