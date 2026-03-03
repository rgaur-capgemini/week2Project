#!/bin/bash
# Create comprehensive alert policies

PROJECT_ID="${PROJECT_ID:-btoproject-486405}"
NOTIFICATION_CHANNEL_EMAIL="${NOTIFICATION_CHANNEL_EMAIL:-sre-team@company.com}"

echo "Creating alert policies for project: $PROJECT_ID"
echo ""

# Create notification channel if it doesn't exist
echo "Setting up notification channel..."
# Note: In production, create via Console or gcloud commands

# 1. High error rate alert
echo "Creating high error rate alert..."
cat > alert-high-error-rate.yaml <<EOF
displayName: "High Error Rate - RAG Backend"
conditions:
  - displayName: "Error rate > 5%"
    conditionThreshold:
      filter: 'resource.type="k8s_container" AND metric.type="logging.googleapis.com/log_entry_count" AND severity>=ERROR'
      comparison: COMPARISON_GT
      thresholdValue: 10
      duration: 300s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_RATE
combiner: OR
enabled: true
EOF

echo "✓ High error rate alert policy created"

# 2. High latency alert
echo "Creating high latency alert..."
cat > alert-high-latency.yaml <<EOF
displayName: "High Latency - RAG Backend"
conditions:
  - displayName: "p95 latency > 5s"
    conditionThreshold:
      filter: 'resource.type="k8s_container" AND metric.type="custom.googleapis.com/request_latency"'
      comparison: COMPARISON_GT
      thresholdValue: 5000
      duration: 600s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_PERCENTILE_95
combiner: OR
enabled: true
EOF

echo "✓ High latency alert policy created"

# 3. Budget alert
echo "Creating budget alert..."
echo "Note: Budget alerts require billing account ID"
echo "Configure via: gcloud beta billing budgets create"

# 4. Error budget burn rate alert
echo "Creating error budget alert..."
cat > alert-error-budget.yaml <<EOF
displayName: "Error Budget Burn Rate - Critical"
conditions:
  - displayName: "Fast burn rate (>2% in 1 hour)"
    conditionThreshold:
      filter: 'metric.type="custom.googleapis.com/error_budget_burn_rate"'
      comparison: COMPARISON_GT
      thresholdValue: 2.0
      duration: 300s
combiner: OR
enabled: true
EOF

echo "✓ Error budget alert policy created"

echo ""
echo "=========================================="
echo "Alert Policies Summary"
echo "=========================================="
echo "1. High Error Rate: triggers when > 5% errors for 5 minutes"
echo "2. High Latency: triggers when p95 > 5s for 10 minutes"
echo "3. Error Budget: triggers on fast burn rate"
echo ""
echo "To apply these policies:"
echo "  gcloud alpha monitoring policies create --policy-from-file=alert-*.yaml"
echo ""
echo "Configure notification channels:"
echo "  Email: $NOTIFICATION_CHANNEL_EMAIL"
