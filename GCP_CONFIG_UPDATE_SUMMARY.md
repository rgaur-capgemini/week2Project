# GCP Configuration - Complete Resource Inventory

**Project**: `botpproject` (430569389330)  
**Region**: `us-central1`  
**Last Verified**: March 7, 2026

---

## ✅ Verified GCP Resources

### 1. Vertex AI - Vector Search

#### Index
- **Resource Name**: `projects/430569389330/locations/us-central1/indexes/5347067982386298880`
- **Index ID**: `5347067982386298880`
- **Display Name**: `rag-chatbot-index`
- **Description**: Vector Search index for RAG chatbot
- **Dimensions**: 768
- **Distance Measure**: DOT_PRODUCT_DISTANCE
- **Algorithm**: TreeAH (Approximate Nearest Neighbor)
- **Shard Size**: MEDIUM
- **Status**: ✅ DEPLOYED

#### Index Endpoint
- **Resource Name**: `projects/430569389330/locations/us-central1/indexEndpoints/332186652006940672`
- **Endpoint ID**: `332186652006940672`
- **Display Name**: `rag-chatbot-endpoint`
- **Public Endpoint Domain**: `69427743.us-central1-430569389330.vdb.vertexai.goog`
- **Public Endpoint Enabled**: ✅ YES
- **Status**: ✅ ACTIVE

#### Deployed Index
- **Deployed Index ID**: `rag_chatbot_deployed`
- **Display Name**: `rag-chatbot-deployed`
- **Index Resource**: `projects/430569389330/locations/us-central1/indexes/5347067982386298880`
- **Min Replicas**: 2
- **Max Replicas**: 2
- **Deployment Group**: default
- **Status**: ✅ DEPLOYED & SYNCED
- **Last Sync**: 2026-03-07 13:55:12 UTC

---

### 2. Redis Memorystore

- **Instance Name**: `rag-redis`
- **Host IP**: `10.200.18.59`
- **Port**: `6379`
- **Region**: `us-central1`
- **Redis Version**: `REDIS_7_0`
- **Memory Size**: 1 GB
- **Tier**: BASIC
- **Authorized Network**: `projects/botpproject/global/networks/default`
- **Status**: ✅ READY

---

### 3. Cloud Storage (GCS)

#### RAG Documents Bucket
- **Bucket Name**: `botpproject-rag-documents`
- **URI**: `gs://botpproject-rag-documents/`
- **Region**: `us-central1`
- **Storage Class**: STANDARD
- **Purpose**: Document storage for RAG pipeline
- **Status**: ✅ ACTIVE

#### CSV Data Bucket
- **Bucket Name**: `botpproject-csv-data`
- **URI**: `gs://botpproject-csv-data/`
- **Region**: `us-central1`
- **Storage Class**: STANDARD
- **Purpose**: CSV file ingestion pipeline
- **Status**: ✅ ACTIVE

---

### 4. Pub/Sub

- **Topic Name**: `csv-ingestion-topic`
- **Resource Name**: `projects/botpproject/topics/csv-ingestion-topic`
- **Purpose**: Trigger CSV file processing pipeline
- **Status**: ✅ ACTIVE

---

### 5. IAM - Service Accounts

#### Primary Service Account
- **Email**: `rag-service@botpproject.iam.gserviceaccount.com`
- **Purpose**: Primary service account for backend services
- **Status**: ✅ ACTIVE

#### K8s Backend Service Account (WIP)
- **Email**: `chatbot-rag-backend@botpproject.iam.gserviceaccount.com`
- **Purpose**: Workload Identity binding for GKE backend pods
- **Status**: ⚠️ TO BE CREATED

#### K8s Frontend Service Account (WIP)
- **Email**: `chatbot-rag-frontend@botpproject.iam.gserviceaccount.com`
- **Purpose**: Workload Identity binding for GKE frontend pods
- **Status**: ⚠️ TO BE CREATED

---

### 6. Artifact Registry

- **Repository Name**: `rag-service` (NOT chatbot-rag-images!)
- **Location**: `us-central1`
- **Format**: DOCKER
- **Mode**: STANDARD_REPOSITORY
- **Full Path**: `us-central1-docker.pkg.dev/botpproject/rag-service`
- **Size**: 0.000 MB (empty - no images pushed yet)
- **Status**: ✅ ACTIVE

**Image Paths**:
- Backend: `us-central1-docker.pkg.dev/botpproject/rag-service/backend:latest`
- Frontend: `us-central1-docker.pkg.dev/botpproject/rag-service/frontend:latest`

---

### 7. Secret Manager

#### chatbot-jwt-secret
- **Purpose**: JWT signing key for authentication
- **Status**: ✅ EXISTS

#### google-oauth-client-id
- **Value**: `430569389330-t6c0ek7vsj9tbtpcmh1ljsnhr8hslpma.apps.googleusercontent.com`
- **Purpose**: Google OAuth 2.0 client ID
- **Status**: ✅ EXISTS

#### google-oauth-client-secret
- **Purpose**: Google OAuth 2.0 client secret
- **Status**: ✅ EXISTS

---

### 8. Firestore

- **Database Name**: `(default)`
- **Type**: `FIRESTORE_NATIVE`
- **Location**: `us-central1`
- **Purpose**: Persistent storage for RAG chunks and metadata
- **Collection**: `rag_chunks`
- **Status**: ✅ ACTIVE

---

### 9. VPC Network

- **Network Name**: `default`
- **Mode**: AUTO
- **Subnets**: Auto-created regional subnets
- **Status**: ✅ ACTIVE

**Connected Services**:
- ✅ Redis Memorystore (10.200.18.59)
- ⚠️ GKE Cluster (NOT CREATED YET)

---

### 10. GKE - Kubernetes Engine

- **Status**: ⚠️ **NO CLUSTER EXISTS**
- **Expected Cluster Name**: `chatbot-rag-gke`
- **Expected Zone**: `us-central1-a`
- **Action Required**: Create GKE cluster before deployment

---

### 11. Cloud Functions

- **Status**: ⚠️ **NO FUNCTIONS DEPLOYED**
- **Expected**: CSV processor function for Pub/Sub trigger
- **Action Required**: Deploy Cloud Function if needed

---

### 12. Cloud Run

- **Status**: ⚠️ **NO SERVICES DEPLOYED**
- **Action Required**: Deploy if using Cloud Run instead of GKE

---

## 📋 Configuration Files Updated

### Core Configuration
1. ✅ `app/config.py`
   - PROJECT_ID: `botpproject`
   - VERTEX_INDEX_ID: `5347067982386298880`
   - VERTEX_INDEX_ENDPOINT: `332186652006940672`
   - DEPLOYED_INDEX_ID: `rag_chatbot_deployed`
   - REDIS_HOST: `10.200.18.59`
   - GCS_BUCKET: `botpproject-rag-documents`
   - GCS_CSV_BUCKET: `botpproject-csv-data`
   - PUBSUB_CSV_TOPIC: `csv-ingestion-topic`

### Kubernetes Manifests
2. ✅ `k8s/backend-deployment.yaml`
   - Image: `us-central1-docker.pkg.dev/botpproject/rag-service/backend:latest`
   - PROJECT_ID: `botpproject`
   - PROJECT_NUMBER: `430569389330`
   - All Vertex AI IDs updated
   - REDIS_HOST: `10.200.18.59`
   - ADMIN_EMAILS: `raman.gaur@capgemini.com`
   - GOOGLE_CLIENT_ID: From secret

3. ✅ `k8s/frontend-deployment.yaml`
   - Image: `us-central1-docker.pkg.dev/botpproject/rag-service/frontend:latest`

4. ✅ `k8s/configmap.yaml`
   - PROJECT_ID: `botpproject`
   - REDIS_HOST: `10.200.18.59`

5. ✅ `k8s/service-account.yaml`
   - GCP SA: `chatbot-rag-backend@botpproject.iam.gserviceaccount.com`
   - GCP SA: `chatbot-rag-frontend@botpproject.iam.gserviceaccount.com`

### CI/CD Pipeline
6. ✅ `ci/cloudbuild-gke.yaml`
   - _PROJECT_ID: `botpproject`
   - _ARTIFACT_REGISTRY: `us-central1-docker.pkg.dev/botpproject/rag-service`
   - All image tags updated to use `rag-service` repository

### Scripts
7. ✅ `scripts/setup_gcp_resources.sh`
   - PROJECT_ID: `botpproject`

8. ✅ `scripts/manual_template_upload.py`
   - PROJECT_ID: `botpproject`

### Documentation
9. ✅ All `.md` files updated with correct resource IDs

---

## 🔧 Environment Variables (Production)

```bash
# GCP Project
PROJECT_ID=botpproject
PROJECT_NUMBER=430569389330
REGION=us-central1

# Vertex AI
VERTEX_LOCATION=us-central1
VERTEX_INDEX_ID=5347067982386298880
VERTEX_INDEX_ENDPOINT=332186652006940672
DEPLOYED_INDEX_ID=rag_chatbot_deployed

# Models
MODEL_VARIANT=gemini-2.0-flash-001
EMBEDDING_MODEL=text-embedding-004
EMBEDDING_DIMENSION=768

# Redis
REDIS_HOST=10.200.18.59
REDIS_PORT=6379
REDIS_DB_HISTORY=0
REDIS_DB_ANALYTICS=1

# Storage
GCS_BUCKET=botpproject-rag-documents
GCS_CSV_BUCKET=botpproject-csv-data

# Pub/Sub
PUBSUB_CSV_TOPIC=csv-ingestion-topic

# Auth
ADMIN_EMAILS=raman.gaur@capgemini.com
GOOGLE_CLIENT_ID=430569389330-t6c0ek7vsj9tbtpcmh1ljsnhr8hslpma.apps.googleusercontent.com

# Firestore
USE_FIRESTORE=true
FIRESTORE_COLLECTION=rag_chunks

# Artifact Registry
ARTIFACT_REGISTRY=us-central1-docker.pkg.dev/botpproject/rag-service
```

---

## ✅ Verification Commands

### Test Vertex AI Index
```bash
gcloud ai indexes describe 5347067982386298880 \
  --project=botpproject \
  --region=us-central1
```

### Test Redis Connection
```bash
# From Cloud Shell or GKE pod
redis-cli -h 10.200.18.59 -p 6379 PING
# Expected: PONG
```

### Test GCS Buckets
```bash
gsutil ls gs://botpproject-rag-documents/
gsutil ls gs://botpproject-csv-data/
```

### Test Pub/Sub Topic
```bash
gcloud pubsub topics describe csv-ingestion-topic --project=botpproject
```

### Test Secret Access
```bash
gcloud secrets versions access latest --secret=google-oauth-client-id
# Expected: 430569389330-t6c0ek7vsj9tbtpcmh1ljsnhr8hslpma.apps.googleusercontent.com
```

---

## ⚠️ Action Items Before Deployment

### 1. Create GKE Cluster
```bash
gcloud container clusters create chatbot-rag-gke \
  --project=botpproject \
  --zone=us-central1-a \
  --num-nodes=3 \
  --machine-type=e2-standard-4 \
  --enable-autoscaling \
  --min-nodes=3 \
  --max-nodes=10 \
  --enable-autorepair \
  --enable-autoupgrade \
  --enable-workload-identity \
  --network=default \
  --subnetwork=default
```

### 2. Create GKE Service Accounts
```bash
# Backend SA
gcloud iam service-accounts create chatbot-rag-backend \
  --project=botpproject \
  --display-name="RAG Chatbot Backend Service Account"

# Frontend SA
gcloud iam service-accounts create chatbot-rag-frontend \
  --project=botpproject \
  --display-name="RAG Chatbot Frontend Service Account"
```

### 3. Configure Workload Identity
```bash
# Backend binding
gcloud iam service-accounts add-iam-policy-binding \
  chatbot-rag-backend@botpproject.iam.gserviceaccount.com \
  --project=botpproject \
  --role=roles/iam.workloadIdentityUser \
  --member="serviceAccount:botpproject.svc.id.goog[default/rag-backend-sa]"

# Frontend binding
gcloud iam service-accounts add-iam-policy-binding \
  chatbot-rag-frontend@botpproject.iam.gserviceaccount.com \
  --project=botpproject \
  --role=roles/iam.workloadIdentityUser \
  --member="serviceAccount:botpproject.svc.id.goog[default/rag-frontend-sa]"
```

### 4. Grant IAM Permissions
```bash
# Vertex AI permissions
gcloud projects add-iam-policy-binding botpproject \
  --member="serviceAccount:chatbot-rag-backend@botpproject.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# GCS permissions
gcloud projects add-iam-policy-binding botpproject \
  --member="serviceAccount:chatbot-rag-backend@botpproject.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# Secret Manager permissions
gcloud projects add-iam-policy-binding botpproject \
  --member="serviceAccount:chatbot-rag-backend@botpproject.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Firestore permissions
gcloud projects add-iam-policy-binding botpproject \
  --member="serviceAccount:chatbot-rag-backend@botpproject.iam.gserviceaccount.com" \
  --role="roles/datastore.user"
```

### 5. Push Docker Images
```bash
# Build and push backend
docker build -t us-central1-docker.pkg.dev/botpproject/rag-service/backend:latest .
docker push us-central1-docker.pkg.dev/botpproject/rag-service/backend:latest

# Build and push frontend
docker build -t us-central1-docker.pkg.dev/botpproject/rag-service/frontend:latest -f frontend/Dockerfile frontend/
docker push us-central1-docker.pkg.dev/botpproject/rag-service/frontend:latest
```

---

## 📊 Resource Status Summary

| Resource | Status | Action Needed |
|----------|--------|---------------|
| Vertex AI Index | ✅ Active | None |
| Vertex AI Endpoint | ✅ Active | None |
| Deployed Index | ✅ Synced | None |
| Redis Memorystore | ✅ Ready | None |
| GCS Buckets (2) | ✅ Active | None |
| Pub/Sub Topic | ✅ Active | None |
| Service Account | ✅ Active | Grant IAM roles |
| Artifact Registry | ✅ Active | Push images |
| Secret Manager (3) | ✅ Active | None |
| Firestore | ✅ Active | None |
| VPC Network | ✅ Active | None |
| GKE Cluster | ❌ Missing | **CREATE CLUSTER** |
| K8s Service Accounts | ❌ Missing | **CREATE AFTER CLUSTER** |
| Cloud Functions | ❌ Missing | Optional (for CSV) |
| Docker Images | ❌ Missing | **BUILD & PUSH** |

---

**Configuration Complete**: ✅ All files updated  
**Ready for Deployment**: ⚠️ After creating GKE cluster and pushing images  
**Last Updated**: March 7, 2026


## Updated Project Configuration

### Project Details
- **Old Project**: `btoproject-486405-486604` (382685100652)
- **New Project**: `botpproject` (430569389330)
- **Region**: `us-central1`
- **Environment**: `production`

---

## Updated Resources

### 1. Vertex AI Vector Search

#### Index Configuration
- **Index ID**: `5347067982386298880` ✅
  - Old: `4892433118440456192`
- **Display Name**: `rag-chatbot-index`
- **Description**: Vector Search index for RAG chatbot
- **Dimensions**: 768
- **Distance Measure**: DOT_PRODUCT_DISTANCE
- **Algorithm**: TreeAH (Approximate Nearest Neighbor)

#### Index Endpoint Configuration
- **Endpoint ID**: `332186652006940672` ✅
  - Old: `7605324128349847552`
- **Display Name**: `rag-chatbot-endpoint`
- **Public Endpoint**: `69427743.us-central1-430569389330.vdb.vertexai.goog`
- **Public Endpoint Enabled**: Yes

#### Deployed Index Configuration
- **Deployed Index ID**: `rag_chatbot_deployed` ✅
  - Old: `chatbot_rag_deployed_1770440353081`
- **Display Name**: `rag-chatbot-deployed`
- **Min Replicas**: 2
- **Max Replicas**: 2
- **Status**: DEPLOYED and SYNCED

---

### 2. Redis Memorystore

- **Instance Name**: `rag-redis`
- **Host IP**: `10.200.18.59` ✅
  - Old: `10.168.174.3`
- **Port**: `6379`
- **Region**: `us-central1`

---

### 3. Cloud Storage (GCS)

- **Bucket Name**: `botpproject-rag-documents` ✅
- **Region**: `us-central1`
- **Storage Class**: STANDARD
- **Purpose**: Document storage for RAG pipeline

---

### 4. Pub/Sub

- **Topic Name**: `csv-ingestion-topic`
- **Project**: `botpproject`
- **Purpose**: CSV file ingestion pipeline

---

### 5. IAM Service Accounts

- **Primary Service Account**: `rag-service@botpproject.iam.gserviceaccount.com` ✅
- **Backend K8s SA**: `chatbot-rag-backend@botpproject.iam.gserviceaccount.com`
- **Frontend K8s SA**: `chatbot-rag-frontend@botpproject.iam.gserviceaccount.com`

---

### 6. Artifact Registry

- **Registry URL**: `us-central1-docker.pkg.dev/botpproject/chatbot-rag-images` ✅
  - Old: `us-central1-docker.pkg.dev/btoproject-486405-486604/chatbot-rag-images`
- **Backend Image**: `chatbot-rag-images/backend:latest`
- **Frontend Image**: `chatbot-rag-images/frontend:latest`

---

### 7. Admin Configuration

- **Admin Email**: `raman.gaur@capgemini.com` ✅
- **Role**: Admin (full access to all features and APIs)
- **Auth Method**: Google OAuth + Custom JWT

---

## Files Updated

### Core Configuration Files
1. ✅ `app/config.py` - Updated PROJECT_ID, Vertex AI IDs, Redis host
2. ✅ `k8s/backend-deployment.yaml` - Updated all environment variables
3. ✅ `k8s/frontend-deployment.yaml` - Updated image registry
4. ✅ `k8s/configmap.yaml` - Updated PROJECT_ID and Redis host
5. ✅ `k8s/service-account.yaml` - Updated service account emails
6. ✅ `ci/cloudbuild-gke.yaml` - Updated project and registry references
7. ✅ `scripts/setup_gcp_resources.sh` - Updated PROJECT_ID
8. ✅ `scripts/manual_template_upload.py` - Updated PROJECT_ID

### Documentation Files
9. ✅ `README.md` - Updated project references
10. ✅ `k8s/README.md` - Updated service account and project references
11. ✅ `QUICK_START_WEEK3.md` - Updated Vertex AI IDs
12. ✅ `WEEK3_IMPLEMENTATION.md` - Updated Vertex AI IDs
13. ✅ `PUBSUB_SETUP_GUIDE.md` - Updated project and Vertex AI IDs
14. ✅ `PRODUCTION_READINESS_REPORT.md` - Updated Vertex AI IDs
15. ✅ `PRODUCTION_CHECKLIST.md` - Updated Vertex AI IDs
16. ✅ `docs/CLOUD_FUNCTION_DEPLOYMENT.md` - Updated Vertex AI IDs

---

## Configuration Validation

### Environment Variables (Backend)
```bash
PROJECT_ID=botpproject
PROJECT_NUMBER=430569389330
REGION=us-central1
VERTEX_LOCATION=us-central1
VERTEX_INDEX_ID=5347067982386298880
VERTEX_INDEX_ENDPOINT=332186652006940672
DEPLOYED_INDEX_ID=rag_chatbot_deployed
REDIS_HOST=10.200.18.59
REDIS_PORT=6379
ADMIN_EMAILS=raman.gaur@capgemini.com
```

### Model Configuration
```bash
MODEL_VARIANT=gemini-2.0-flash-001
EMBEDDING_MODEL=text-embedding-004
EMBEDDING_DIMENSION=768
MAX_TOKENS=8000
```

---

## Next Steps

### 1. Verify Vertex AI Index Deployment
```bash
gcloud ai indexes describe 5347067982386298880 \
  --project=botpproject \
  --region=us-central1
```

### 2. Test Redis Connection
```bash
# From within GKE pod or Cloud Shell with VPC access
redis-cli -h 10.200.18.59 -p 6379 PING
```

### 3. Verify GCS Bucket Access
```bash
gsutil ls gs://botpproject-rag-documents/
```

### 4. Test Vector Search Endpoint
```bash
curl -X POST \
  https://69427743.us-central1-430569389330.vdb.vertexai.goog/v1/projects/430569389330/locations/us-central1/indexEndpoints/332186652006940672:findNeighbors \
  -H "Authorization: Bearer $(gcloud auth print-access-token)"
```

---

## Migration Checklist

- [x] Update project ID from `btoproject-486405-486604` to `botpproject`
- [x] Update project number from `382685100652` to `430569389330`
- [x] Update Vertex AI Index ID to `5347067982386298880`
- [x] Update Vertex AI Index Endpoint to `332186652006940672`
- [x] Update Deployed Index ID to `rag_chatbot_deployed`
- [x] Update Redis host to `10.200.18.59`
- [x] Update Artifact Registry paths
- [x] Update service account emails
- [x] Update all documentation files
- [ ] Deploy to GKE cluster (cluster needs to be created)
- [ ] Test end-to-end RAG pipeline
- [ ] Verify admin access with `raman.gaur@capgemini.com`

---

## Notes

1. **GKE Cluster**: No GKE cluster exists yet in `botpproject`. You'll need to create one before deploying.
2. **Secrets**: Ensure all secrets (SENDGRID_API_KEY, REDIS_PASSWORD, JWT keys) are created in Secret Manager.
3. **IAM Permissions**: Service accounts need proper IAM roles for Vertex AI, GCS, Pub/Sub access.
4. **Network**: Ensure Redis VPC is accessible from GKE cluster.

---

**Last Updated**: March 7, 2026  
**Status**: Configuration files updated, ready for deployment
