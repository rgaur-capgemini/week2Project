# Cloud Function Deployment Guide - Template Processor

## Overview

This guide explains how to deploy the Cloud Function that processes uploaded compliance templates asynchronously.

### Architecture

```
Template Upload Flow:
1. User uploads template → Backend API
2. Backend uploads to GCS
3. Backend publishes Pub/Sub message
4. Cloud Function triggered → processes template
5. Cloud Function chunks, embeds, stores in Vector Search
6. Template ready for compliance checking
```

## Prerequisites

- ✅ GCP project with billing enabled
- ✅ Cloud Functions, Cloud Build, Pub/Sub APIs enabled
- ✅ Service account with required permissions
- ✅ Pub/Sub topic `compliance-template-ingestion` created
- ✅ GCS bucket for templates created

## Deployment Steps

### Option 1: Automated Deployment (Recommended)

Run the deployment script in Cloud Shell:

```bash
# Download and run deployment script
curl -o deploy_cloud_function.sh \
  https://raw.githubusercontent.com/rgaur-capgemini/week2Project/develop/scripts/deploy_cloud_function.sh

chmod +x deploy_cloud_function.sh
./deploy_cloud_function.sh
```

### Option 2: Manual Deployment

#### Step 1: Enable APIs

```bash
PROJECT_ID="btoproject-486405-486604"
REGION="us-central1"

gcloud services enable cloudfunctions.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  eventarc.googleapis.com \
  --project=${PROJECT_ID}
```

#### Step 2: Grant IAM Permissions

```bash
SERVICE_ACCOUNT="chatbot-rag-backend@${PROJECT_ID}.iam.gserviceaccount.com"

# Pub/Sub subscriber
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/pubsub.subscriber"

# Firestore access
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/datastore.user"

# Vertex AI access
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/aiplatform.user"

# Storage access
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/storage.objectAdmin"
```

#### Step 3: Get Vertex AI Configuration

```bash
# From existing deployment
VERTEX_INDEX_ID="4892433118440456192"
VERTEX_INDEX_ENDPOINT="7605324128349847552"
DEPLOYED_INDEX_ID="chatbot_rag_deployed_1770440353081"

# Or get from ConfigMap
kubectl get configmap rag-config -o yaml
```

#### Step 4: Clone Repository

```bash
git clone https://github.com/rgaur-capgemini/week2Project.git
cd week2Project
git checkout develop
cd cloud-functions/template-processor
```

#### Step 5: Deploy Function

```bash
gcloud functions deploy compliance-template-processor \
  --gen2 \
  --runtime=python311 \
  --region=${REGION} \
  --source=. \
  --entry-point=process_template \
  --trigger-topic=compliance-template-ingestion \
  --service-account=${SERVICE_ACCOUNT} \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},REGION=${REGION},VERTEX_INDEX_ID=${VERTEX_INDEX_ID},VERTEX_INDEX_ENDPOINT=${VERTEX_INDEX_ENDPOINT},DEPLOYED_INDEX_ID=${DEPLOYED_INDEX_ID}" \
  --memory=1024MB \
  --timeout=540s \
  --max-instances=10 \
  --project=${PROJECT_ID}
```

**Deployment takes 3-5 minutes**

## Verification

### Check Function Status

```bash
# Get function details
gcloud functions describe compliance-template-processor \
  --region=${REGION} \
  --project=${PROJECT_ID}

# Check for ACTIVE state
```

### Verify Pub/Sub Subscription

```bash
# List subscriptions to the topic
gcloud pubsub topics list-subscriptions compliance-template-ingestion \
  --project=${PROJECT_ID}

# Should show: gcf-compliance-template-processor-...
```

### Test Template Upload

```bash
# Upload a test template
export TOKEN="your-jwt-token"

curl -X POST "http://34.28.73.87/compliance/templates/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@iso27001-template.txt" \
  -F "template_type=ISO27001" \
  -F "version=1.0"

# Expected response:
{
  "template_id": "uuid",
  "status": "processing",
  "message": "Template uploaded successfully. Processing via Cloud Function."
}
```

### Monitor Function Logs

```bash
# Real-time logs
gcloud functions logs read compliance-template-processor \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --limit=50 \
  --format=json

# Filter for specific template
gcloud functions logs read compliance-template-processor \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --limit=100 | grep "template_id"
```

### Check Firestore

```bash
# Check template metadata
# Navigate to: https://console.cloud.google.com/firestore
# Collection: compliance_templates
# Should see document with template_id

# Check template chunks
# Collection: compliance_template_chunks
# Should see multiple documents with template_id
```

### Verify Vector Store

The function stores embeddings in Firestore temporarily. To verify:

```bash
# Count chunks
gcloud firestore databases documents list \
  --collection-ids=compliance_template_chunks \
  --project=${PROJECT_ID} \
  | wc -l

# Should show number of chunks created
```

## Troubleshooting

### Function Not Triggering

**Check Pub/Sub subscription:**
```bash
gcloud pubsub subscriptions list --project=${PROJECT_ID}

# If missing, create manually:
gcloud pubsub subscriptions create gcf-compliance-template-processor \
  --topic=compliance-template-ingestion \
  --push-endpoint=https://${REGION}-${PROJECT_ID}.cloudfunctions.net/compliance-template-processor
```

### Permission Errors

**Grant missing roles:**
```bash
# Check current roles
gcloud projects get-iam-policy ${PROJECT_ID} \
  --flatten="bindings[].members" \
  --filter="bindings.members:${SERVICE_ACCOUNT}"

# Grant all required roles
for role in "roles/pubsub.subscriber" "roles/datastore.user" "roles/aiplatform.user" "roles/storage.objectAdmin"; do
  gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="$role"
done
```

### Function Timeout

**Increase timeout:**
```bash
gcloud functions deploy compliance-template-processor \
  --timeout=540s \
  --update-env-vars=... \
  --region=${REGION} \
  --project=${PROJECT_ID}
```

### High Latency

**Increase memory allocation:**
```bash
gcloud functions deploy compliance-template-processor \
  --memory=2048MB \
  --update-env-vars=... \
  --region=${REGION} \
  --project=${PROJECT_ID}
```

### Check Function Logs for Errors

```bash
# View errors
gcloud functions logs read compliance-template-processor \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --limit=100 \
  | grep -i "error\|exception\|failed"

# View specific execution
gcloud functions logs read compliance-template-processor \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --execution-id=EXECUTION_ID
```

## Cost Considerations

**Cloud Function Pricing (us-central1):**
- Invocations: First 2M free, then $0.40 per million
- GB-seconds: First 400,000 free, then $0.0000025 per GB-second
- GHz-seconds: First 200,000 free, then $0.00001 per GHz-second

**Estimated Monthly Cost:**
- 1,000 template uploads/month
- Average 30 seconds processing time
- 1 GB memory
- **Cost: ~$0.10 - $0.50/month**

## Performance Optimization

### Batch Processing

For multiple templates, use batch upload:

```bash
# Upload multiple templates
for template in *.txt; do
  curl -X POST "http://34.28.73.87/compliance/templates/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$template" \
    -F "template_type=ISO27001" \
    -F "version=1.0"
  sleep 2  # Rate limiting
done
```

### Monitoring

Set up alerts:

```bash
# Create log-based metric
gcloud logging metrics create template_processing_errors \
  --description="Template processing errors" \
  --log-filter='resource.type="cloud_function"
resource.labels.function_name="compliance-template-processor"
severity>=ERROR' \
  --project=${PROJECT_ID}

# Create alerting policy in Cloud Console
```

## Rollback

If issues occur, rollback to previous version:

```bash
# List versions
gcloud functions describe compliance-template-processor \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --format="value(updateTime,versionId)"

# Rollback
gcloud functions deploy compliance-template-processor \
  --source=gs://gcf-sources-${PROJECT_ID}/... \
  --region=${REGION} \
  --project=${PROJECT_ID}
```

## Cleanup

To remove the Cloud Function:

```bash
gcloud functions delete compliance-template-processor \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --quiet
```

## Alternative: Inline Processing

If Cloud Function deployment is not feasible, the backend API has a fallback that processes templates inline. This works but:
- ❌ Slower response time (30-60 seconds)
- ❌ Blocks API thread
- ❌ No retry on failure
- ✅ No additional infrastructure needed

The current implementation will automatically fallback to inline processing if Pub/Sub publish fails.

## Next Steps

After deploying the Cloud Function:

1. **Test template upload** - Upload a template and verify it processes
2. **Check Firestore** - Verify template metadata stored
3. **Upload compliance document** - Test document comparison
4. **Monitor logs** - Watch for any errors
5. **Set up alerts** - Configure monitoring
6. **Update backend** - Remove inline processing fallback (optional)

## Support

For issues:
1. Check function logs: `gcloud functions logs read ...`
2. Verify Pub/Sub subscription exists
3. Check service account permissions
4. Review Firestore for template data
5. Test with simple text template first
