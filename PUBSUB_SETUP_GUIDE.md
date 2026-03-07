# Google Pub/Sub Setup Guide for Week 3 Compliance System

## Overview
Your Week 3 implementation **DOES include Pub/Sub** for asynchronous template processing. Here's what you need to configure in GCP.

---

## 📋 What's Already in Your Code

### 1. **Publisher (Backend FastAPI)**
**File:** `app/compliance_routes.py` (Line 353-375)
- Publishes template upload messages to Pub/Sub topic
- Topic name: `compliance-template-ingestion`
- Fallback: Direct processing if Pub/Sub unavailable

### 2. **Subscriber (Cloud Function)**
**File:** `cloud-functions/template-processor/main.py` (Line 82-120)
- Triggered by Pub/Sub messages
- Processes templates asynchronously
- Chunks, embeds, and stores in Vector Search

---

## 🔧 Required GCP Configuration

### Step 1: Enable Pub/Sub API

```bash
# Enable the Pub/Sub API for your project
gcloud services enable pubsub.googleapis.com --project=btoproject-486405
```

**Verify:**
```bash
gcloud services list --enabled --filter="name:pubsub" --project=btoproject-486405
```

---

### Step 2: Create Pub/Sub Topic

```bash
# Create the topic that your backend will publish to
gcloud pubsub topics create compliance-template-ingestion \
  --project=btoproject-486405 \
  --message-retention-duration=7d \
  --labels=app=compliance,environment=production
```

**Verify:**
```bash
gcloud pubsub topics describe compliance-template-ingestion --project=btoproject-486405
```

**Expected Output:**
```
name: projects/btoproject-486405/topics/compliance-template-ingestion
labels:
  app: compliance
  environment: production
messageRetentionDuration: 604800s
```

---

### Step 3: Create GCS Bucket for Templates

```bash
# Create bucket for compliance templates (if not exists)
gcloud storage buckets create gs://btoproject-486405-compliance-templates \
  --project=btoproject-486405 \
  --location=us-central1 \
  --uniform-bucket-level-access
```

**Verify:**
```bash
gcloud storage buckets describe gs://btoproject-486405-compliance-templates
```

---

### Step 4: Deploy Cloud Function (Gen2)

**Prerequisites:**
- Cloud Functions API enabled
- Cloud Build API enabled
- Artifact Registry API enabled

```bash
# Enable required APIs
gcloud services enable cloudfunctions.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  --project=btoproject-486405

# Deploy the Cloud Function
cd cloud-functions/template-processor

gcloud functions deploy compliance-template-processor \
  --gen2 \
  --runtime=python311 \
  --region=us-central1 \
  --source=. \
  --entry-point=process_template \
  --trigger-topic=compliance-template-ingestion \
  --memory=2Gi \
  --timeout=540s \
  --max-instances=10 \
  --min-instances=0 \
  --service-account=<YOUR_SERVICE_ACCOUNT>@btoproject-486405.iam.gserviceaccount.com \
  --set-env-vars="PROJECT_ID=btoproject-486405,REGION=us-central1,VERTEX_INDEX_ID=5347067982386298880,VERTEX_INDEX_ENDPOINT=332186652006940672,DEPLOYED_INDEX_ID=rag_chatbot_deployed" \
  --project=btoproject-486405
```

**Note:** Replace `<YOUR_SERVICE_ACCOUNT>` with your Cloud Function service account name.

**Verify Deployment:**
```bash
gcloud functions describe compliance-template-processor \
  --gen2 \
  --region=us-central1 \
  --project=btoproject-486405
```

---

### Step 5: Grant IAM Permissions

#### A. Backend Service Account (FastAPI on GKE)
Your backend needs permission to **publish** to Pub/Sub:

```bash
# Get your GKE service account (usually Compute Engine default or custom SA)
GKE_SA="<YOUR_GKE_SERVICE_ACCOUNT>@btoproject-486405.iam.gserviceaccount.com"

# Grant Pub/Sub Publisher role
gcloud projects add-iam-policy-binding btoproject-486405 \
  --member="serviceAccount:${GKE_SA}" \
  --role="roles/pubsub.publisher"

# Grant GCS access to upload templates
gcloud storage buckets add-iam-policy-binding gs://btoproject-486405-compliance-templates \
  --member="serviceAccount:${GKE_SA}" \
  --role="roles/storage.objectCreator"
```

#### B. Cloud Function Service Account
Your Cloud Function needs multiple permissions:

```bash
# Get Cloud Function service account
CF_SA="<YOUR_CF_SERVICE_ACCOUNT>@btoproject-486405.iam.gserviceaccount.com"

# Grant Pub/Sub Subscriber (automatically granted when using --trigger-topic)
# But verify:
gcloud projects add-iam-policy-binding btoproject-486405 \
  --member="serviceAccount:${CF_SA}" \
  --role="roles/pubsub.subscriber"

# Grant GCS access to download templates
gcloud storage buckets add-iam-policy-binding gs://btoproject-486405-compliance-templates \
  --member="serviceAccount:${CF_SA}" \
  --role="roles/storage.objectViewer"

# Grant Firestore access
gcloud projects add-iam-policy-binding btoproject-486405 \
  --member="serviceAccount:${CF_SA}" \
  --role="roles/datastore.user"

# Grant Vertex AI access
gcloud projects add-iam-policy-binding btoproject-486405 \
  --member="serviceAccount:${CF_SA}" \
  --role="roles/aiplatform.user"
```

---

### Step 6: Verify Pub/Sub Configuration

#### Check Topic
```bash
gcloud pubsub topics describe compliance-template-ingestion --project=btoproject-486405
```

#### Check Subscription (Auto-created by Cloud Function)
```bash
# List subscriptions
gcloud pubsub subscriptions list --project=btoproject-486405

# Should see something like:
# eventarc-us-central1-compliance-template-processor-<hash>
```

#### Test Publishing Manually
```bash
# Publish a test message
gcloud pubsub topics publish compliance-template-ingestion \
  --project=btoproject-486405 \
  --message='{"template_id":"test-123","template_type":"ISO27001","bucket":"btoproject-486405-compliance-templates","blob_name":"test.pdf"}'
```

**Check Cloud Function Logs:**
```bash
gcloud functions logs read compliance-template-processor \
  --gen2 \
  --region=us-central1 \
  --limit=50 \
  --project=btoproject-486405
```

---

## 📊 Architecture Flow

```
┌─────────────────────┐
│  Admin uploads      │
│  template via API   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────────┐
│  FastAPI Backend (compliance_routes.py)     │
│  POST /compliance/templates/upload          │
│                                              │
│  1. Upload file to GCS                      │
│     gs://...-compliance-templates/...       │
│                                              │
│  2. Publish message to Pub/Sub              │
│     Topic: compliance-template-ingestion    │
│                                              │
│  3. Return "processing" status              │
└──────────┬──────────────────────────────────┘
           │
           │ Pub/Sub Message
           ▼
┌─────────────────────────────────────────────┐
│  Cloud Function Gen2                        │
│  compliance-template-processor              │
│                                              │
│  Triggered by Pub/Sub                       │
│                                              │
│  1. Download from GCS                       │
│  2. Chunk document (1000 words)             │
│  3. Generate embeddings (text-embedding-004)│
│  4. Store in Vertex AI Vector Search        │
│  5. Update Firestore metadata               │
│  6. (Optional) Send email notification      │
└──────────┬──────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────┐
│  Template Ready for Compliance Checks       │
│  Available in vector search                 │
└─────────────────────────────────────────────┘
```

---

## 🔍 What's Different from Week 1-2

| Component | Week 1-2 (Existing) | Week 3 (New) |
|-----------|---------------------|--------------|
| **Pub/Sub Topics** | None (or other topics) | `compliance-template-ingestion` |
| **Cloud Functions** | None (or other functions) | `compliance-template-processor` |
| **GCS Buckets** | `btoproject-486405-rag-documents` | `btoproject-486405-compliance-templates` (NEW) |
| **Firestore Collections** | `rag_chunks`, `chat_history` | `compliance_reports`, `compliance_templates` (NEW) |
| **API Routes** | `/api/query`, `/api/ingest` | `/compliance/*` (NEW) |

**Important:** Your existing Week 1-2 infrastructure is **NOT affected**. Week 3 adds parallel infrastructure.

---

## 🚨 Common Issues & Solutions

### Issue 1: "Topic not found" Error
**Symptom:** Backend throws error when publishing
**Solution:**
```bash
# Check if topic exists
gcloud pubsub topics list --project=btoproject-486405 | grep compliance

# Create if missing
gcloud pubsub topics create compliance-template-ingestion --project=btoproject-486405
```

### Issue 2: "Permission denied" on Pub/Sub
**Symptom:** 403 error when publishing
**Solution:**
```bash
# Grant publisher role to your backend service account
gcloud projects add-iam-policy-binding btoproject-486405 \
  --member="serviceAccount:<YOUR_SA>@btoproject-486405.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher"
```

### Issue 3: Cloud Function Not Triggered
**Symptom:** Messages published but function doesn't execute
**Solution:**
```bash
# Check function deployment
gcloud functions describe compliance-template-processor --gen2 --region=us-central1

# Check subscription exists
gcloud pubsub subscriptions list | grep template-processor

# Check function logs for errors
gcloud functions logs read compliance-template-processor --gen2 --region=us-central1
```

### Issue 4: Template Bucket Not Found
**Symptom:** GCS upload fails
**Solution:**
```bash
# Create bucket
gcloud storage buckets create gs://btoproject-486405-compliance-templates \
  --location=us-central1 \
  --project=btoproject-486405

# Grant access to backend service account
gcloud storage buckets add-iam-policy-binding gs://btoproject-486405-compliance-templates \
  --member="serviceAccount:<YOUR_SA>@btoproject-486405.iam.gserviceaccount.com" \
  --role="roles/storage.objectCreator"
```

---

## 📝 Configuration Checklist

### ✅ Pre-Deployment
- [ ] Pub/Sub API enabled
- [ ] Cloud Functions API enabled
- [ ] Pub/Sub topic created (`compliance-template-ingestion`)
- [ ] GCS bucket created (`btoproject-486405-compliance-templates`)
- [ ] Service accounts identified (GKE SA, Cloud Function SA)

### ✅ IAM Permissions
- [ ] Backend SA has `roles/pubsub.publisher`
- [ ] Backend SA has `roles/storage.objectCreator` on templates bucket
- [ ] Cloud Function SA has `roles/pubsub.subscriber`
- [ ] Cloud Function SA has `roles/storage.objectViewer` on templates bucket
- [ ] Cloud Function SA has `roles/datastore.user`
- [ ] Cloud Function SA has `roles/aiplatform.user`

### ✅ Deployment
- [ ] Cloud Function deployed successfully
- [ ] Cloud Function environment variables set
- [ ] Pub/Sub subscription auto-created
- [ ] Test message processed successfully

### ✅ Testing
- [ ] Manually publish test message
- [ ] Check Cloud Function logs
- [ ] Verify Firestore document created
- [ ] Verify Vector Search updated

---

## 🎯 Quick Deployment Script

Save this as `deploy-pubsub-setup.sh`:

```bash
#!/bin/bash
set -e

PROJECT_ID="btoproject-486405"
REGION="us-central1"
TOPIC_NAME="compliance-template-ingestion"
BUCKET_NAME="${PROJECT_ID}-compliance-templates"
FUNCTION_NAME="compliance-template-processor"

echo "🚀 Deploying Week 3 Pub/Sub Infrastructure..."

# 1. Enable APIs
echo "📦 Enabling APIs..."
gcloud services enable pubsub.googleapis.com \
  cloudfunctions.googleapis.com \
  cloudbuild.googleapis.com \
  --project=${PROJECT_ID}

# 2. Create Pub/Sub topic
echo "📨 Creating Pub/Sub topic..."
gcloud pubsub topics create ${TOPIC_NAME} \
  --project=${PROJECT_ID} \
  --message-retention-duration=7d || echo "Topic already exists"

# 3. Create GCS bucket
echo "🪣 Creating GCS bucket..."
gcloud storage buckets create gs://${BUCKET_NAME} \
  --project=${PROJECT_ID} \
  --location=${REGION} \
  --uniform-bucket-level-access || echo "Bucket already exists"

# 4. Deploy Cloud Function
echo "☁️ Deploying Cloud Function..."
cd cloud-functions/template-processor
gcloud functions deploy ${FUNCTION_NAME} \
  --gen2 \
  --runtime=python311 \
  --region=${REGION} \
  --source=. \
  --entry-point=process_template \
  --trigger-topic=${TOPIC_NAME} \
  --memory=2Gi \
  --timeout=540s \
  --max-instances=10 \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},REGION=${REGION}" \
  --project=${PROJECT_ID}

echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Grant IAM permissions to service accounts"
echo "2. Test with: gcloud pubsub topics publish ${TOPIC_NAME} --message='test'"
echo "3. Check logs: gcloud functions logs read ${FUNCTION_NAME} --gen2 --region=${REGION}"
```

**Run:**
```bash
chmod +x deploy-pubsub-setup.sh
./deploy-pubsub-setup.sh
```

---

## 📊 Monitoring

### View Pub/Sub Metrics
```bash
# Topic metrics (in GCP Console)
# Navigation: Pub/Sub > Topics > compliance-template-ingestion > Metrics
```

### View Cloud Function Metrics
```bash
# Function metrics (in GCP Console)
# Navigation: Cloud Functions > compliance-template-processor > Metrics
```

### Set Up Alerts
```bash
# Alert for unacknowledged messages (backlog)
gcloud alpha monitoring policies create \
  --notification-channels=<channel-id> \
  --display-name="Pub/Sub Backlog Alert" \
  --condition-display-name="Unacked messages > 100" \
  --condition-threshold-value=100 \
  --condition-threshold-duration=300s
```

---

## 📚 Additional Resources

- **Pub/Sub Documentation:** https://cloud.google.com/pubsub/docs
- **Cloud Functions Gen2:** https://cloud.google.com/functions/docs/2nd-gen/overview
- **Your Implementation Guide:** `WEEK3_IMPLEMENTATION.md`
- **Quick Start:** `QUICK_START_WEEK3.md`

---

**Last Updated:** February 16, 2026  
**Status:** ✅ Implementation Complete - Configuration Required
