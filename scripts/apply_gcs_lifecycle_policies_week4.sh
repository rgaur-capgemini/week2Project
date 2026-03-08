#!/bin/bash
# GCS Lifecycle Policy Setup - Week 4
# Applies lifecycle policies for cost optimization

set -e

PROJECT_ID="${1:-botpproject}"
BUCKET_NAME="${2:-${PROJECT_ID}-rag-documents}"

echo "========================================"
echo "GCS Lifecycle Policy Setup"
echo "========================================"
echo "Project: $PROJECT_ID"
echo "Bucket: $BUCKET_NAME"
echo ""

# Create lifecycle policy JSON
cat > /tmp/lifecycle-policy.json << 'EOF'
{
  "lifecycle": {
    "rule": [
      {
        "action": {
          "type": "SetStorageClass",
          "storageClass": "NEARLINE"
        },
        "condition": {
          "age": 30,
          "matchesPrefix": ["documents/"]
        }
      },
      {
        "action": {
          "type": "SetStorageClass",
          "storageClass": "COLDLINE"
        },
        "condition": {
          "age": 90,
          "matchesPrefix": ["documents/", "backups/"]
        }
      },
      {
        "action": {
          "type": "SetStorageClass",
          "storageClass": "ARCHIVE"
        },
        "condition": {
          "age": 180,
          "matchesPrefix": ["archives/", "backups/"]
        }
      },
      {
        "action": {
          "type": "Delete"
        },
        "condition": {
          "age": 365,
          "matchesPrefix": ["temp/", "logs/"]
        }
      },
      {
        "action": {
          "type": "Delete"
        },
        "condition": {
          "daysSinceNoncurrentTime": 30,
          "numNewerVersions": 3
        }
      }
    ]
  }
}
EOF

echo "[1/4] Lifecycle policy created"
cat /tmp/lifecycle-policy.json
echo ""

# Apply lifecycle policy
echo "[2/4] Applying lifecycle policy to bucket..."
gsutil lifecycle set /tmp/lifecycle-policy.json gs://$BUCKET_NAME
echo "✓ Lifecycle policy applied"
echo ""

# Verify policy
echo "[3/4] Verifying lifecycle policy..."
gsutil lifecycle get gs://$BUCKET_NAME
echo ""

# Create cost optimization report
echo "[4/4] Generating cost optimization report..."

cat > cost-optimization-report.txt << EOF
========================================
GCS Lifecycle Cost Optimization Report
========================================
Date: $(date)
Project: $PROJECT_ID
Bucket: $BUCKET_NAME

LIFECYCLE POLICIES APPLIED:
---------------------------

1. NEARLINE Transition (30 days)
   - Applies to: documents/
   - Storage cost: 65% reduction
   - Access cost: Slightly higher
   - Best for: Infrequently accessed documents

2. COLDLINE Transition (90 days)
   - Applies to: documents/, backups/
   - Storage cost: 80% reduction
   - Access cost: Higher
   - Best for: Archived documents

3. ARCHIVE Transition (180 days)
   - Applies to: archives/, backups/
   - Storage cost: 90% reduction
   - Access cost: Highest
   - Best for: Long-term archives

4. Auto-deletion (365 days)
   - Applies to: temp/, logs/
   - Complete removal of temporary files

5. Version Management
   - Keep only 3 most recent versions
   - Delete older versions after 30 days

ESTIMATED COST SAVINGS:
-----------------------
- Storage costs: 40-60% reduction
- Overall GCS costs: 30-50% reduction
- Monthly savings: $$50-200 (depending on usage)

MONITORING:
-----------
- Check storage class distribution monthly
- Review access patterns quarterly
- Adjust policies based on usage

Next Steps:
1. Monitor cost impact in Cloud Billing
2. Review object storage classes monthly
3. Adjust lifecycle rules based on usage patterns

EOF

cat cost-optimization-report.txt
echo ""

echo "✓ Lifecycle policies configured successfully!"
echo ""
echo "Cost savings will be visible in 30-90 days"
echo "Monitor progress: gcloud alpha billing accounts list"

# _week4
