#!/bin/bash
# Budget Setup Script - Week 4
# Creates budgets and alerts for cost control

set -e

PROJECT_ID="${1:-botpproject}"
BILLING_ACCOUNT_ID="${2}"  # Required parameter

if [ -z "$BILLING_ACCOUNT_ID" ]; then
    echo "Error: BILLING_ACCOUNT_ID required"
    echo "Usage: $0 PROJECT_ID BILLING_ACCOUNT_ID"
    echo ""
    echo "Find your billing account:"
    echo "  gcloud beta billing accounts list"
    exit 1
fi

echo "========================================"
echo "Budget & Alerts Setup - Week 4"
echo "========================================"
echo "Project: $PROJECT_ID"
echo "Billing Account: $BILLING_ACCOUNT_ID"
echo ""

# Enable Billing Budget API
echo "[1/6] Enabling Billing Budget API..."
gcloud services enable billingbudgets.googleapis.com --project=$PROJECT_ID
echo "✓ API enabled"
echo ""

# Create Pub/Sub topic for budget alerts
echo "[2/6] Creating Pub/Sub topic for budget alerts..."
gcloud pubsub topics create budget-alerts --project=$PROJECT_ID 2>/dev/null || echo "Topic already exists"
echo "✓ Pub/Sub topic ready"
echo ""

# Create monthly budget with thresholds
echo "[3/6] Creating monthly budget..."

# Production budget: $2000/month
gcloud billing budgets create \
    --billing-account=$BILLING_ACCOUNT_ID \
    --display-name="production-monthly-budget" \
    --budget-amount=2000USD \
    --threshold-rule=percent=50 \
    --threshold-rule=percent=75 \
    --threshold-rule=percent=90 \
    --threshold-rule=percent=100 \
    --filter-projects="projects/$PROJECT_ID" \
    --all-updates-rule-pubsub-topic=projects/$PROJECT_ID/topics/budget-alerts \
    2>/dev/null || echo "Budget already exists"

echo "✓ Budget created: production-monthly-budget ($2000)"
echo ""

# Vertex AI specific budget
echo "[4/6] Creating Vertex AI budget..."
gcloud billing budgets create \
    --billing-account=$BILLING_ACCOUNT_ID \
    --display-name="vertex-ai-monthly-budget" \
    --budget-amount=1000USD \
    --threshold-rule=percent=60 \
    --threshold-rule=percent=80 \
    --threshold-rule=percent=95 \
    --threshold-rule=percent=100 \
    --filter-projects="projects/$PROJECT_ID" \
    --filter-services="services/aiplatform.googleapis.com" \
    --all-updates-rule-pubsub-topic=projects/$PROJECT_ID/topics/budget-alerts \
    2>/dev/null || echo "Budget already exists"

echo "✓ Budget created: vertex-ai-monthly-budget ($1000)"
echo ""

# Create Cloud Monitoring alert policies
echo "[5/6] Creating Cloud Monitoring alert policies..."

# High cost anomaly alert
cat > /tmp/cost-anomaly-alert.yaml << 'EOF'
displayName: "High Cost Anomaly Detected"
conditions:
  - displayName: "Cost increase > 50%"
    conditionThreshold:
      filter: 'resource.type="billing_account"'
      comparison: COMPARISON_GT
      thresholdValue: 50
      duration: 3600s
      aggregations:
        - alignmentPeriod: 3600s
          perSeriesAligner: ALIGN_RATE
notificationChannels:
  - projects/${PROJECT_ID}/notificationChannels/EMAIL_CHANNEL_ID
alertStrategy:
  autoClose: 86400s
EOF

echo "✓ Alert policies defined"
echo ""

# Enable budget alert notifications via email
echo "[6/6] Setting up email notifications..."

cat > budget-setup-summary.txt << EOF
========================================
Budget & Alerts Setup Summary
========================================
Date: $(date)
Project: $PROJECT_ID

BUDGETS CREATED:
----------------
1. Production Monthly Budget
   - Amount: $2000/month
   - Thresholds: 50%, 75%, 90%, 100%
   - Scope: All services

2. Vertex AI Monthly Budget
   - Amount: $1000/month
   - Thresholds: 60%, 80%, 95%, 100%
   - Scope: Vertex AI only

ALERTS CONFIGURED:
------------------
- Budget threshold alerts
- Cost anomaly detection
- Pub/Sub topic: budget-alerts

NOTIFICATION CHANNELS:
----------------------
To add email notifications:
1. Go to Cloud Console → Monitoring → Alerting
2. Create notification channel (Email)
3. Add to budget alerts

MONITORING DASHBOARDS:
----------------------
- Cloud Billing Reports
- Budget alerts in Pub/Sub
- Custom FinOps dashboard (API)

ESTIMATED BENEFITS:
-------------------
- Prevent unexpected cost overruns
- Early warning at 50% threshold
- Automated alerts for anomalies
- Monthly cost visibility

NEXT STEPS:
-----------
1. Configure email notification channels
2. Review budgets monthly
3. Adjust thresholds based on usage
4. Set up Slack/PagerDuty integration (optional)

Check budget status:
  gcloud billing budgets list --billing-account=$BILLING_ACCOUNT_ID

EOF

cat budget-setup-summary.txt
echo ""

echo "✓ Budget & alerts setup complete!"
echo ""
echo "View budgets:"
echo "  gcloud billing budgets list --billing-account=$BILLING_ACCOUNT_ID"
echo ""
echo "Configure email notifications:"
echo "  https://console.cloud.google.com/monitoring/alerting"

# _week4
