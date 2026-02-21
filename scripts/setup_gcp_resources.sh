#!/bin/bash
# Script to set up GCP resources for compliance features
# Run this in Cloud Shell

set -e

PROJECT_ID="btoproject-486405-486604"
REGION="us-central1"
SERVICE_ACCOUNT="chatbot-rag-backend@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=== Setting up GCP Resources for Compliance Features ==="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo ""

# 1. Create Pub/Sub topic for template ingestion
echo "1. Creating Pub/Sub topic..."
gcloud pubsub topics create compliance-template-ingestion \
  --project=${PROJECT_ID} \
  --message-retention-duration=7d \
  || echo "Topic already exists"

# 2. Create compliance templates bucket
echo ""
echo "2. Creating compliance templates bucket..."
gsutil mb -p ${PROJECT_ID} -c STANDARD -l ${REGION} \
  gs://${PROJECT_ID}-compliance-templates \
  || echo "Bucket already exists"

# 3. Grant Pub/Sub permissions
echo ""
echo "3. Granting Pub/Sub permissions to service account..."
gcloud pubsub topics add-iam-policy-binding compliance-template-ingestion \
  --project=${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/pubsub.publisher"

# 4. Grant storage permissions for templates bucket
echo ""
echo "4. Granting storage permissions..."
gsutil iam ch serviceAccount:${SERVICE_ACCOUNT}:objectAdmin \
  gs://${PROJECT_ID}-compliance-templates

# 5. Create SendGrid secret (if not exists)
echo ""
echo "5. Creating SendGrid secret placeholder..."
echo "Please set your SendGrid API key:"
echo "  gcloud secrets create sendgrid-api-key --replication-policy='automatic' --project=${PROJECT_ID}"
echo "  echo -n 'YOUR_SENDGRID_API_KEY' | gcloud secrets versions add sendgrid-api-key --data-file=- --project=${PROJECT_ID}"
echo ""
echo "Grant secret access to service account:"
echo "  gcloud secrets add-iam-policy-binding sendgrid-api-key \\"
echo "    --member='serviceAccount:${SERVICE_ACCOUNT}' \\"
echo "    --role='roles/secretmanager.secretAccessor' \\"
echo "    --project=${PROJECT_ID}"

# 6. Verify setup
echo ""
echo "=== Verification ==="
echo ""
echo "Pub/Sub topics:"
gcloud pubsub topics list --project=${PROJECT_ID} | grep compliance

echo ""
echo "Buckets:"
gsutil ls | grep compliance

echo ""
echo "Service account roles:"
gcloud projects get-iam-policy ${PROJECT_ID} \
  --flatten="bindings[].members" \
  --filter="bindings.members:${SERVICE_ACCOUNT}" \
  --format="table(bindings.role)"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Set SendGrid API key as shown above"
echo "2. Update k8s/configmap.yaml with FROM_EMAIL"
echo "3. Commit changes and trigger build"
echo "4. Deploy to GKE"
