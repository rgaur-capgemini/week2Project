#!/bin/bash
# Set up synthetic monitoring with Cloud Scheduler

PROJECT_ID="${PROJECT_ID:-btoproject-486405}"
REGION="${REGION:-us-central1}"
BACKEND_URL="${BACKEND_URL:-http://rag-backend-service}"

echo "Setting up synthetic monitoring for project: $PROJECT_ID"
echo ""

# 1. Create uptime check
echo "Creating uptime check..."
gcloud monitoring uptime-checks create http rag-backend-uptime \
  --project=$PROJECT_ID \
  --display-name="RAG Backend Uptime" \
  --resource-type=uptime-url \
  --host="rag-backend-service" \
  --path="/health" \
  --check-interval=60s \
  --timeout=10s \
  2>/dev/null || echo "Uptime check may already exist"

echo "✓ Uptime check configured"

# 2. Create Cloud Scheduler job for synthetic tests
echo ""
echo "Creating Cloud Scheduler job for synthetic monitoring..."
gcloud scheduler jobs create http synthetic-health-check \
  --project=$PROJECT_ID \
  --location=$REGION \
  --schedule="*/5 * * * *" \
  --uri="$BACKEND_URL/health" \
  --http-method=GET \
  --max-retry-attempts=3 \
  --max-retry-duration=600s \
  2>/dev/null || echo "Scheduler job may already exist"

echo "✓ Cloud Scheduler job configured"

# 3. Create synthetic monitoring script
echo ""
echo "Synthetic monitoring configured:"
echo "  - Uptime check: Every 60 seconds"
echo "  - Scheduled tests: Every 5 minutes"
echo "  - Health endpoint: $BACKEND_URL/health"
echo ""
echo "To view uptime checks:"
echo "  gcloud monitoring uptime-checks list --project=$PROJECT_ID"
echo ""
echo "To view scheduler jobs:"
echo "  gcloud scheduler jobs list --location=$REGION --project=$PROJECT_ID"
