#!/bin/bash
# Create log-based metrics for alerting

PROJECT_ID="${PROJECT_ID:-btoproject-486405}"

echo "Creating log-based metrics for project: $PROJECT_ID"
echo ""

# 1. Compliance workflow failures
echo "Creating metric: compliance_workflow_failures..."
gcloud logging metrics create compliance_workflow_failures \
  --project=$PROJECT_ID \
  --description="Count of failed compliance workflows" \
  --log-filter='resource.type="k8s_container"
    AND jsonPayload.message=~"Error in compliance workflow"
    AND severity>=ERROR' \
  2>/dev/null || echo "Metric may already exist"

# 2. Vertex AI API errors
echo "Creating metric: vertex_ai_errors..."
gcloud logging metrics create vertex_ai_errors \
  --project=$PROJECT_ID \
  --description="Vertex AI API errors" \
  --log-filter='resource.type="k8s_container"
    AND jsonPayload.message=~"Vertex.*error"
    AND severity>=ERROR' \
  2>/dev/null || echo "Metric may already exist"

# 3. Authentication failures
echo "Creating metric: auth_failures..."
gcloud logging metrics create auth_failures \
  --project=$PROJECT_ID \
  --description="Authentication failures" \
  --log-filter='resource.type="k8s_container"
    AND jsonPayload.message=~"Authentication failed"
    AND severity>=WARNING' \
  2>/dev/null || echo "Metric may already exist"

# 4. High latency requests (>5s)
echo "Creating metric: high_latency_requests..."
gcloud logging metrics create high_latency_requests \
  --project=$PROJECT_ID \
  --description="Requests with latency > 5s" \
  --log-filter='resource.type="k8s_container"
    AND jsonPayload.duration_seconds>5' \
  2>/dev/null || echo "Metric may already exist"

echo ""
echo "✓ Log-based metrics created"
echo ""
echo "View metrics at:"
echo "  https://console.cloud.google.com/logs/metrics?project=$PROJECT_ID"
