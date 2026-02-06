# GCP Console Configuration Guide
## Step-by-Step Setup for Production Deployment

> **Project**: btoproject-486405  
> **Region**: us-central1  
> **Deployment**: Cloud Run (Fast) or GKE (Production)

---

## 🎯 Pre-Deployment Checklist

- [ ] GCP Project created: `btoproject-486405`
- [ ] Billing account linked
- [ ] Owner/Editor permissions granted
- [ ] gcloud CLI installed and authenticated
- [ ] Terraform installed (>= 1.6.0)

---

## 📋 Part 1: Enable Required APIs

### Via GCP Console:
1. Go to **APIs & Services → Library**
2. Search and enable each API:
   - ✅ Vertex AI API (`aiplatform.googleapis.com`)
   - ✅ Cloud Run API (`run.googleapis.com`)
   - ✅ Cloud Build API (`cloudbuild.googleapis.com`)
   - ✅ Artifact Registry API (`artifactregistry.googleapis.com`)
   - ✅ Secret Manager API (`secretmanager.googleapis.com`)
   - ✅ Cloud Memorystore for Redis API (`redis.googleapis.com`)
   - ✅ Kubernetes Engine API (`container.googleapis.com`)
   - ✅ Cloud Storage API (`storage.googleapis.com`)
   - ✅ Firestore API (`firestore.googleapis.com`)
   - ✅ Identity and Access Management (IAM) API (`iam.googleapis.com`)

### Via gcloud CLI:
```bash
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  redis.googleapis.com \
  container.googleapis.com \
  storage.googleapis.com \
  firestore.googleapis.com \
  iam.googleapis.com \
  --project=btoproject-486405
```

---

## 🔐 Part 2: Configure Authentication (Google OAuth)

### 2.1 Create OAuth 2.0 Credentials
1. Navigate to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Configure consent screen if prompted:
   - User Type: **External**
   - App name: `ChatBot RAG Application`
   - User support email: Your email
   - Developer contact: Your email
   - Scopes: `email`, `profile`, `openid`
   - Test users: Add your Gmail accounts
4. Select Application type: **Web application**
5. Name: `ChatBot Frontend`
6. Authorized JavaScript origins:
   ```
   http://localhost:4200
   https://YOUR-FRONTEND-DOMAIN.com
   https://YOUR-CLOUD-RUN-URL.run.app
   ```
7. Authorized redirect URIs:
   ```
   http://localhost:4200/login
   https://YOUR-FRONTEND-DOMAIN.com/login
   ```
8. Click **Create**
9. **SAVE** the Client ID and Client Secret

### 2.2 Store OAuth Credentials in Secret Manager
```bash
# Store Client ID
echo -n "YOUR_CLIENT_ID.apps.googleusercontent.com" | \
  gcloud secrets create google-oauth-client-id \
  --data-file=- \
  --replication-policy="automatic"

# Store Client Secret
echo -n "YOUR_CLIENT_SECRET" | \
  gcloud secrets create google-oauth-client-secret \
  --data-file=- \
  --replication-policy="automatic"
```

### 2.3 Create JWT Secret
```bash
# Generate and store random JWT key
openssl rand -base64 32 | \
  gcloud secrets create rag-jwt-key \
  --data-file=- \
  --replication-policy="automatic"
```

---

## 🧠 Part 3: Set Up Vertex AI Vector Search

### 3.1 Create Vector Search Index

**Via GCP Console:**

1. Navigate to **Vertex AI → Vector Search**
2. Click **Create Index**
3. Configure:
   - **Index name**: `rag-index`
   - **Description**: RAG chatbot document embeddings
   - **Region**: `us-central1`
   - **Dimensions**: `768` (for text-embedding-004 model)
   - **Distance measure**: `Cosine similarity`
   - **Shard size**: `SHARD_SIZE_SMALL` (for <1M vectors)
   - **Update method**: `Streaming` (for real-time updates)
4. Click **Create** (takes ~10-15 minutes)
5. **Note the Index ID** (format: `projects/123/locations/us-central1/indexes/456`)

### 3.2 Create Index Endpoint

1. Go to **Vertex AI → Vector Search → Index Endpoints**
2. Click **Create Endpoint**
3. Configure:
   - **Endpoint name**: `rag-index-endpoint`
   - **Region**: `us-central1`
   - **Network**: Default (or select VPC if using GKE)
4. Click **Create**
5. **Note the Endpoint ID**

### 3.3 Deploy Index to Endpoint

1. Go to your Index Endpoint
2. Click **Deploy Index**
3. Select:
   - **Index**: `rag-index`
   - **Deployed index ID**: `rag-index-deployed`
   - **Machine type**: `e2-standard-2` (for development) or `e2-standard-8` (production)
   - **Min replicas**: `1` (dev) or `2` (prod)
   - **Max replicas**: `2` (dev) or `10` (prod)
4. Click **Deploy** (takes ~20-30 minutes)

**Via gcloud CLI:**
```bash
# Note: Replace IDs after creating via console
export VERTEX_INDEX_ID="projects/btoproject-486405/locations/us-central1/indexes/YOUR_INDEX_ID"
export VERTEX_ENDPOINT_ID="projects/btoproject-486405/locations/us-central1/indexEndpoints/YOUR_ENDPOINT_ID"

# Deploy index
gcloud ai index-endpoints deploy-index $VERTEX_ENDPOINT_ID \
  --deployed-index-id=rag-index-deployed \
  --index=$VERTEX_INDEX_ID \
  --display-name="RAG Index Deployment" \
  --machine-type=e2-standard-2 \
  --min-replica-count=1 \
  --max-replica-count=2
```

---

## 🔴 Part 4: Create Cloud Memorystore Redis

### 4.1 Create Redis Instance

**Via GCP Console:**

1. Navigate to **Memorystore → Redis**
2. Click **Create Instance**
3. Configure:
   - **Instance ID**: `rag-redis`
   - **Tier**: `Standard` (HA with automatic failover)
   - **Region**: `us-central1`
   - **Capacity**: `1 GB` (dev) or `5 GB` (production)
   - **Redis version**: `7.0`
   - **Network**: Default or select VPC
   - **IP range**: Leave default or specify
   - **Connection mode**: `Private Service Access`
4. Click **Create** (takes ~5-10 minutes)
5. **Note the Internal IP** from instance details

**Via gcloud CLI:**
```bash
gcloud redis instances create rag-redis \
  --size=1 \
  --region=us-central1 \
  --tier=standard \
  --redis-version=redis_7_0 \
  --network=default

# Get connection details
gcloud redis instances describe rag-redis \
  --region=us-central1 \
  --format="value(host,port)"
```

**Expected Output:**
```
10.0.0.3  # Host IP
6379      # Port
```

---

## 📦 Part 5: Create Cloud Storage Bucket

### 5.1 Create GCS Bucket for Documents

**Via GCP Console:**

1. Navigate to **Cloud Storage → Buckets**
2. Click **Create**
3. Configure:
   - **Name**: `btoproject-486405-rag-documents`
   - **Location type**: `Region`
   - **Location**: `us-central1`
   - **Storage class**: `Standard`
   - **Access control**: `Uniform`
   - **Protection tools**: Enable versioning (optional)
4. Click **Create**

**Via gcloud CLI:**
```bash
gsutil mb -p btoproject-486405 \
  -c STANDARD \
  -l us-central1 \
  gs://btoproject-486405-rag-documents
```

### 5.2 Create GCS Bucket for Frontend (Static Hosting)

```bash
gsutil mb -p btoproject-486405 \
  -c STANDARD \
  -l us-central1 \
  gs://btoproject-486405-frontend

# Configure as website
gsutil web set -m index.html -e index.html gs://btoproject-486405-frontend

# Make public
gsutil iam ch allUsers:objectViewer gs://btoproject-486405-frontend
```

---

## 🔧 Part 6: Configure Firestore

### 6.1 Initialize Firestore

**Via GCP Console:**

1. Navigate to **Firestore**
2. Click **Select Native Mode**
3. Choose:
   - **Location**: `us-central1` (must match other resources)
4. Click **Create Database**
5. No further setup needed - collections are created automatically

**Via gcloud CLI:**
```bash
gcloud firestore databases create --region=us-central1
```

---

## 🏗️ Part 7: Create Service Accounts

### 7.1 Create Backend Service Account

```bash
# Create service account
gcloud iam service-accounts create rag-backend-sa \
  --display-name="RAG Backend Service Account" \
  --description="Service account for RAG backend with AI and storage access"

# Grant necessary roles
gcloud projects add-iam-policy-binding btoproject-486405 \
  --member="serviceAccount:rag-backend-sa@btoproject-486405.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding btoproject-486405 \
  --member="serviceAccount:rag-backend-sa@btoproject-486405.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding btoproject-486405 \
  --member="serviceAccount:rag-backend-sa@btoproject-486405.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding btoproject-486405 \
  --member="serviceAccount:rag-backend-sa@btoproject-486405.iam.gserviceaccount.com" \
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding btoproject-486405 \
  --member="serviceAccount:rag-backend-sa@btoproject-486405.iam.gserviceaccount.com" \
  --role="roles/redis.editor"
```

---

## 🚀 Part 8: Deploy Backend to Cloud Run

### 8.1 Build Container Image

```bash
cd week2_btoproject_cloudrun_full

# Build with Cloud Build
gcloud builds submit \
  --tag gcr.io/btoproject-486405/rag-backend:latest \
  --project btoproject-486405
```

### 8.2 Deploy to Cloud Run

```bash
gcloud run deploy rag-backend \
  --image gcr.io/btoproject-486405/rag-backend:latest \
  --platform managed \
  --region us-central1 \
  --service-account rag-backend-sa@btoproject-486405.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --concurrency 80 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars "\
PROJECT_ID=btoproject-486405,\
REGION=us-central1,\
VERTEX_LOCATION=us-central1,\
VERTEX_INDEX_ID=YOUR_INDEX_ID,\
VERTEX_INDEX_ENDPOINT=YOUR_ENDPOINT_ID,\
DEPLOYED_INDEX_ID=rag-index-deployed,\
MODEL_VARIANT=gemini-2.0-flash-001,\
EMBEDDING_MODEL=text-embedding-004,\
REDIS_HOST=YOUR_REDIS_HOST,\
REDIS_PORT=6379,\
GCS_BUCKET=btoproject-486405-rag-documents,\
FIRESTORE_COLLECTION=rag_chunks,\
USE_FIRESTORE=true,\
LOG_LEVEL=INFO"
```

**Get Backend URL:**
```bash
gcloud run services describe rag-backend \
  --region us-central1 \
  --format="value(status.url)"
```

---

## 🎨 Part 9: Deploy Frontend

### Option A: Cloud Storage (Static Hosting)

```bash
cd frontend

# Update environment with backend URL
# Edit: src/environments/environment.prod.ts
# Set: apiUrl: 'https://YOUR-BACKEND-URL.run.app/api/v1'

# Build production bundle
npm run build:prod

# Upload to GCS
gsutil -m rsync -r -d dist/chatbot-frontend gs://btoproject-486405-frontend

# Get public URL
echo "https://storage.googleapis.com/btoproject-486405-frontend/index.html"
```

### Option B: Cloud Run (Containerized)

```bash
cd frontend

# Build container
gcloud builds submit \
  --tag gcr.io/btoproject-486405/rag-frontend:latest

# Deploy
gcloud run deploy rag-frontend \
  --image gcr.io/btoproject-486405/rag-frontend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 5
```

---

## 🧪 Part 10: Test Deployment

### 10.1 Health Check

```bash
export BACKEND_URL="https://rag-backend-xyz-uc.a.run.app"

curl $BACKEND_URL/health
# Expected: {"status":"healthy"}

curl $BACKEND_URL/readiness
# Expected: {"ready":true}
```

### 10.2 Run Smoke Tests

```bash
cd week2_btoproject_cloudrun_full
export APP_URL=$BACKEND_URL
python scripts/smoke_tests.py
```

### 10.3 Test Authentication Flow

1. Open frontend URL in browser
2. Click "Sign in with Google"
3. Authorize application
4. Verify redirect to chat screen

### 10.4 Test RAG Query

```bash
# Upload a test document
curl -X POST $BACKEND_URL/api/v1/ingest \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@test-document.pdf"

# Query
curl -X POST $BACKEND_URL/api/v1/chat/query \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"What is in the document?","top_k":5}'
```

---

## 📊 Part 11: Set Up Monitoring

### 11.1 Create Uptime Check

**Via GCP Console:**

1. Navigate to **Monitoring → Uptime checks**
2. Click **Create Uptime Check**
3. Configure:
   - **Title**: `RAG Backend Health`
   - **Check type**: `HTTPS`
   - **Resource type**: `URL`
   - **Hostname**: `rag-backend-xyz-uc.a.run.app`
   - **Path**: `/health`
   - **Check frequency**: `1 minute`
4. Click **Test** then **Create**

### 11.2 Create Alerting Policy

1. In **Monitoring → Alerting**
2. Click **Create Policy**
3. Add condition:
   - **Target**: Uptime check metric
   - **Condition**: `Check passed = False`
   - **Duration**: `2 minutes`
4. Configure notifications:
   - **Email**: Your email
5. Save policy

---

## 🔐 Part 12: Security Hardening

### 12.1 Enable Cloud Armor (Optional - WAF)

```bash
# Create security policy
gcloud compute security-policies create rag-waf-policy \
  --description="WAF for RAG application"

# Add rate limiting rule
gcloud compute security-policies rules create 1000 \
  --security-policy=rag-waf-policy \
  --expression="true" \
  --action=rate-based-ban \
  --rate-limit-threshold-count=100 \
  --rate-limit-threshold-interval-sec=60 \
  --ban-duration-sec=600
```

### 12.2 Restrict Cloud Run Ingress

```bash
gcloud run services update rag-backend \
  --region us-central1 \
  --ingress=internal-and-cloud-load-balancing
```

---

## ✅ Deployment Verification Checklist

- [ ] All APIs enabled
- [ ] OAuth credentials created and configured
- [ ] JWT secret stored in Secret Manager
- [ ] Vertex AI Vector Search index created and deployed
- [ ] Cloud Memorystore Redis instance running
- [ ] GCS buckets created
- [ ] Firestore initialized
- [ ] Service account created with proper IAM roles
- [ ] Backend deployed to Cloud Run with all env vars
- [ ] Frontend deployed and accessible
- [ ] Health checks passing
- [ ] Authentication flow working
- [ ] RAG query successful
- [ ] Monitoring and alerts configured

---

## 🆘 Troubleshooting

### Issue: "Permission Denied" errors

**Solution:**
```bash
# Check service account permissions
gcloud projects get-iam-policy btoproject-486405 \
  --flatten="bindings[].members" \
  --filter="bindings.members:rag-backend-sa@btoproject-486405.iam.gserviceaccount.com"
```

### Issue: Vector Search index not found

**Solution:**
```bash
# List indexes
gcloud ai indexes list --region=us-central1

# Check deployment status
gcloud ai index-endpoints list --region=us-central1
```

### Issue: Redis connection refused

**Solution:**
- Verify Redis instance is running
- Check VPC network connectivity
- Ensure Cloud Run/GKE has access to VPC
- Verify Redis host IP is correct

### Issue: Frontend can't reach backend (CORS)

**Solution:**
- Add frontend domain to CORS allowed origins in `app/main_enhanced.py`
- Redeploy backend

---

## 📞 Support

**GCP Documentation:**
- [Cloud Run](https://cloud.google.com/run/docs)
- [Vertex AI](https://cloud.google.com/vertex-ai/docs)
- [Cloud Memorystore](https://cloud.google.com/memorystore/docs/redis)
- [Secret Manager](https://cloud.google.com/secret-manager/docs)

**Project Support:**
- Implementation Status: See `IMPLEMENTATION_STATUS.md`
- Operations Guide: See `docs/RUNBOOK.md`
- SRE Playbook: See `docs/SRE_PLAYBOOK.md`

---

## 🎯 Estimated Total Setup Time

- **APIs & Prerequisites**: 15 minutes
- **OAuth Setup**: 10 minutes
- **Vertex AI Vector Search**: 30 minutes (including deployment wait time)
- **Cloud Memorystore Redis**: 10 minutes
- **Storage & Firestore**: 5 minutes
- **Service Accounts**: 5 minutes
- **Backend Deployment**: 15 minutes
- **Frontend Deployment**: 10 minutes
- **Testing & Validation**: 15 minutes

**Total**: ~2 hours (including wait times for resource provisioning)

---

**Last Updated**: February 5, 2026  
**Version**: 1.0
