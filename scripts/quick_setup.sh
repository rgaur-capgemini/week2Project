#!/bin/bash
# Quick setup script - Run this in Cloud Shell
# Sets up Pub/Sub, buckets, and prepares for deployment

set -e

PROJECT_ID="botpproject"
SERVICE_ACCOUNT="rag-service@${PROJECT_ID}.iam.gserviceaccount.com"

echo "╔════════════════════════════════════════════════════════╗"
echo "║  GCP Compliance Feature Setup - Quick Start           ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# 1. Create Pub/Sub topic
echo "→ Creating Pub/Sub topic..."
gcloud pubsub topics create compliance-template-ingestion \
  --project=${PROJECT_ID} 2>/dev/null \
  && echo "  ✓ Topic created" \
  || echo "  ✓ Topic already exists"

# 2. Create bucket
echo ""
echo "→ Creating compliance templates bucket..."
gsutil mb -p ${PROJECT_ID} -c STANDARD -l us-central1 \
  gs://${PROJECT_ID}-compliance-templates 2>/dev/null \
  && echo "  ✓ Bucket created" \
  || echo "  ✓ Bucket already exists"

# 3. Grant Pub/Sub permissions
echo ""
echo "→ Granting Pub/Sub permissions..."
gcloud pubsub topics add-iam-policy-binding compliance-template-ingestion \
  --project=${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/pubsub.publisher" > /dev/null 2>&1
echo "  ✓ Permissions granted"

# 4. Grant storage permissions
echo ""
echo "→ Granting storage permissions..."
gsutil iam ch serviceAccount:${SERVICE_ACCOUNT}:objectAdmin \
  gs://${PROJECT_ID}-compliance-templates > /dev/null 2>&1
echo "  ✓ Storage access granted"

# 5. Verification
echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  Verification                                          ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "✓ Pub/Sub Topic: compliance-template-ingestion"
gcloud pubsub topics describe compliance-template-ingestion --project=${PROJECT_ID} --format="value(name)" 2>/dev/null

echo ""
echo "✓ Bucket: gs://${PROJECT_ID}-compliance-templates"
gsutil ls gs://${PROJECT_ID}-compliance-templates 2>&1 | head -1

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  Next Steps                                            ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "1. Set up SendGrid (for email notifications):"
echo "   → Sign up at: https://sendgrid.com/"
echo "   → Generate API key"
echo "   → Run:"
echo ""
echo "   echo -n 'YOUR_SENDGRID_API_KEY' | gcloud secrets versions add sendgrid-api-key --data-file=- --project=${PROJECT_ID}"
echo ""
echo "2. Deploy updated backend:"
echo "   → Trigger Cloud Build or run:"
echo ""
echo "   gcloud builds submit --config=ci/cloudbuild-gke.yaml --project=${PROJECT_ID}"
echo ""
echo "3. Create Kubernetes secret (after deployment):"
echo ""
echo "   API_KEY=\$(gcloud secrets versions access latest --secret=sendgrid-api-key --project=${PROJECT_ID})"
echo "   kubectl create secret generic sendgrid-secret --from-literal=api-key=\"\${API_KEY}\""
echo "   kubectl rollout restart deployment rag-backend"
echo ""
echo "4. Upload ISO27001 template:"
echo ""
echo "   export TOKEN=\"your-jwt-token\""
echo "   curl -X POST \"http://34.28.73.87/compliance/templates/upload\" \\"
echo "     -H \"Authorization: Bearer \$TOKEN\" \\"
echo "     -F \"file=@iso27001-template.txt\" \\"
echo "     -F \"template_type=ISO27001\" \\"
echo "     -F \"version=1.0\""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Setup complete! Ready to deploy. 🚀"
echo ""
