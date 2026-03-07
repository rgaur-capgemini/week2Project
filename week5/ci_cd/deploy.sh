#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# Week 5 – Deployment Script
#
# Usage:
#   ./week5/ci_cd/deploy.sh [environment] [service]
#
# Arguments:
#   environment : dev | staging | production  (default: dev)
#   service     : backend | csv-function | all  (default: all)
#
# Prerequisites:
#   - gcloud CLI authenticated
#   - Docker image already built and pushed to Artifact Registry
#   - Environment variables: PROJECT_ID, REGION (or set in script)
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Config ─────────────────────────────────────
PROJECT_ID="${PROJECT_ID:-botpproject}"
REGION="${REGION:-us-central1}"
REPO="${REPO:-rag-service}"
SERVICE_NAME="${SERVICE_NAME:-rag-service}"
ENV="${1:-dev}"
SERVICE="${2:-all}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$SERVICE_NAME:$IMAGE_TAG"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Week 5 Deployment"
echo "  Environment : $ENV"
echo "  Service     : $SERVICE"
echo "  Project     : $PROJECT_ID"
echo "  Region      : $REGION"
echo "  Image       : $IMAGE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Helper: colour output ──────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Environment-specific config ────────────────
case "$ENV" in
  dev)
    MIN_INSTANCES=0
    MAX_INSTANCES=3
    MEMORY="2Gi"
    CPU=1
    CANARY_PERCENT=0
    ALLOW_UNAUTHENTICATED="--allow-unauthenticated"
    ;;
  staging)
    MIN_INSTANCES=1
    MAX_INSTANCES=5
    MEMORY="4Gi"
    CPU=2
    CANARY_PERCENT=20
    ALLOW_UNAUTHENTICATED="--allow-unauthenticated"
    ;;
  production)
    MIN_INSTANCES=2
    MAX_INSTANCES=10
    MEMORY="4Gi"
    CPU=2
    CANARY_PERCENT=10
    ALLOW_UNAUTHENTICATED="--allow-unauthenticated"
    ;;
  *)
    error "Unknown environment '$ENV'. Use: dev | staging | production"
    ;;
esac

# ── Deploy Cloud Run backend ───────────────────
deploy_backend() {
  info "Deploying Cloud Run backend to $ENV..."

  gcloud run deploy "$SERVICE_NAME" \
    --image="$IMAGE" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --memory="$MEMORY" \
    --cpu="$CPU" \
    --min-instances="$MIN_INSTANCES" \
    --max-instances="$MAX_INSTANCES" \
    --no-traffic \
    --tag="week5-$ENV" \
    --set-env-vars="PROJECT_ID=$PROJECT_ID,ENVIRONMENT=$ENV,MODEL_VARIANT=gemini-2.0-flash-001" \
    --service-account="rag-service@$PROJECT_ID.iam.gserviceaccount.com" \
    $ALLOW_UNAUTHENTICATED \
    --quiet

  # Traffic management
  NEW_REVISION=$(gcloud run revisions list \
    --service="$SERVICE_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format='value(metadata.name)' \
    --limit=1)

  if [ "$CANARY_PERCENT" -gt 0 ] && [ "$ENV" != "dev" ]; then
    STABLE_REVISION=$(gcloud run services describe "$SERVICE_NAME" \
      --region="$REGION" \
      --project="$PROJECT_ID" \
      --format='value(status.traffic[0].revisionName)')

    STABLE_PCT=$((100 - CANARY_PERCENT))
    info "Canary split: stable=$STABLE_PCT% | new=$CANARY_PERCENT%"

    gcloud run services update-traffic "$SERVICE_NAME" \
      --region="$REGION" \
      --project="$PROJECT_ID" \
      --to-revisions="$STABLE_REVISION=$STABLE_PCT,$NEW_REVISION=$CANARY_PERCENT" \
      --quiet
  else
    info "Routing 100% traffic to new revision..."
    gcloud run services update-traffic "$SERVICE_NAME" \
      --region="$REGION" \
      --project="$PROJECT_ID" \
      --to-latest \
      --quiet
  fi

  SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format='value(status.url)')

  info "Backend deployed: $SERVICE_URL"
}

# ── Deploy CSV Cloud Function ──────────────────
deploy_csv_function() {
  info "Deploying CSV Ingestor Cloud Function to $ENV..."

  FUNC_NAME="csv-ingestor-$ENV"

  gcloud functions deploy "$FUNC_NAME" \
    --gen2 \
    --runtime=python311 \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --source=week5/cloud_functions/csv_ingestor/ \
    --entry-point=csv_ingestor \
    --trigger-http \
    --allow-unauthenticated \
    --memory=512MB \
    --timeout=120s \
    --set-env-vars="PROJECT_ID=$PROJECT_ID,GCS_CSV_BUCKET=$PROJECT_ID-csv-data,PUBSUB_TOPIC=csv-ingestion-topic" \
    --quiet

  info "CSV Cloud Function deployed: $FUNC_NAME"
}

# ── Create GCS bucket for CSV if not exists ────
ensure_csv_bucket() {
  BUCKET_NAME="$PROJECT_ID-csv-data"
  if ! gsutil ls "gs://$BUCKET_NAME" &>/dev/null; then
    info "Creating GCS bucket: $BUCKET_NAME"
    gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://$BUCKET_NAME"
    gsutil lifecycle set week5/ci_cd/gcs_lifecycle.json "gs://$BUCKET_NAME" 2>/dev/null || true
  else
    info "GCS bucket already exists: $BUCKET_NAME"
  fi
}

# ── Create Pub/Sub topic if not exists ─────────
ensure_pubsub_topic() {
  TOPIC_NAME="csv-ingestion-topic"
  if ! gcloud pubsub topics describe "$TOPIC_NAME" --project="$PROJECT_ID" &>/dev/null; then
    info "Creating Pub/Sub topic: $TOPIC_NAME"
    gcloud pubsub topics create "$TOPIC_NAME" --project="$PROJECT_ID"
  else
    info "Pub/Sub topic already exists: $TOPIC_NAME"
  fi
}

# ── Run smoke tests ────────────────────────────
run_smoke_tests() {
  info "Running smoke tests..."
  SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format='value(status.url)')

  # Health check
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/health")
  if [ "$HTTP_STATUS" -eq 200 ]; then
    info "Health check PASSED ($HTTP_STATUS)"
  else
    warn "Health check returned $HTTP_STATUS"
  fi

  # Week5 agent health
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/api/v5/agent/health")
  if [ "$HTTP_STATUS" -eq 200 ]; then
    info "Agent health check PASSED ($HTTP_STATUS)"
  else
    warn "Agent health check returned $HTTP_STATUS"
  fi
}

# ── Main ───────────────────────────────────────
ensure_csv_bucket
ensure_pubsub_topic

case "$SERVICE" in
  backend)
    deploy_backend
    ;;
  csv-function)
    deploy_csv_function
    ;;
  all)
    deploy_backend
    deploy_csv_function
    ;;
  *)
    error "Unknown service '$SERVICE'. Use: backend | csv-function | all"
    ;;
esac

run_smoke_tests

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
info "Deployment complete!  ENV=$ENV  SERVICE=$SERVICE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
