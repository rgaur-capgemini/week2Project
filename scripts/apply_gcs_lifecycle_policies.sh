#!/bin/bash
# Apply lifecycle policies to GCS buckets for cost optimization

PROJECT_ID="${PROJECT_ID:-btoproject-486405}"
BUCKET_NAME="${PROJECT_ID}-rag-documents"

echo "Applying GCS lifecycle policies to ${BUCKET_NAME}"

# Create lifecycle policy JSON
cat > lifecycle-policy.json <<EOF
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
          "matchesPrefix": ["documents/"]
        }
      },
      {
        "action": {
          "type": "Delete"
        },
        "condition": {
          "age": 365,
          "matchesPrefix": ["temp/", "cache/"]
        }
      }
    ]
  }
}
EOF

# Apply lifecycle policy
gsutil lifecycle set lifecycle-policy.json gs://${BUCKET_NAME}

echo "✓ Lifecycle policies applied"
echo "  - Move to Nearline after 30 days"
echo "  - Move to Coldline after 90 days"
echo "  - Delete temp files after 365 days"

# Verify
echo ""
echo "Current lifecycle configuration:"
gsutil lifecycle get gs://${BUCKET_NAME}

# Cleanup
rm lifecycle-policy.json

echo ""
echo "Estimated monthly savings: \$50-80"
