
#!/usr/bin/env bash
set -euo pipefail
PROJECT_ID=botpproject
REGION=us-central1
INDEX_ID=5347067982386298880
ENDPOINT_ID=332186652006940672

# Create Index (using gcloud alpha as of now)
gcloud alpha aiplatform vector-indexes create "$INDEX_ID"   --project="$PROJECT_ID" --region="$REGION"   --display-name="RAG-Index"   --dimensions=768   --algorithm-config=tree-ah   --enable-approximate-nearest-neighbor   --labels=env=dev || true

# Create Index Endpoint
gcloud alpha aiplatform vector-index-endpoints create "$ENDPOINT_ID"   --project="$PROJECT_ID" --region="$REGION"   --display-name="RAG-Index-Endpoint" || true
