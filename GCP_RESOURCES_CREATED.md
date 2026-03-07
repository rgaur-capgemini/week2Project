# GCP Resources Creation Summary

**Date**: March 7, 2026  
**Project**: `botpproject` (430569389330)  
**Status**: ✅ Core Infrastructure Created

---

## ✅ Resources Successfully Created

### 1. IAM Service Accounts

#### Backend Service Account
- **Email**: `chatbot-rag-backend@botpproject.iam.gserviceaccount.com`
- **Display Name**: RAG Chatbot Backend Service Account
- **Status**: ✅ CREATED
- **IAM Roles Granted**:
  - ✅ `roles/aiplatform.user` - Vertex AI access
  - ✅ `roles/storage.objectAdmin` - GCS access
  - ✅ `roles/secretmanager.secretAccessor` - Secret Manager access
  - ✅ `roles/datastore.user` - Firestore access
  - ✅ `roles/pubsub.publisher` - Pub/Sub publishing
  - ✅ `roles/logging.logWriter` - Cloud Logging
  - ✅ `roles/monitoring.metricWriter` - Cloud Monitoring

#### Frontend Service Account
- **Email**: `chatbot-rag-frontend@botpproject.iam.gserviceaccount.com`
- **Display Name**: RAG Chatbot Frontend Service Account
- **Status**: ✅ CREATED

---

### 2. Workload Identity Bindings

#### Backend Binding
- **GCP Service Account**: `chatbot-rag-backend@botpproject.iam.gserviceaccount.com`
- **K8s Service Account**: `rag-backend-sa` (namespace: `default`)
- **Workload Pool**: `botpproject.svc.id.goog`
- **IAM Role**: `roles/iam.workloadIdentityUser`
- **Status**: ✅ CONFIGURED

#### Frontend Binding
- **GCP Service Account**: `chatbot-rag-frontend@botpproject.iam.gserviceaccount.com`
- **K8s Service Account**: `rag-frontend-sa` (namespace: `default`)
- **Workload Pool**: `botpproject.svc.id.goog`
- **IAM Role**: `roles/iam.workloadIdentityUser`
- **Status**: ✅ CONFIGURED

---

### 3. GKE Cluster

- **Cluster Name**: `chatbot-rag-gke`
- **Zone**: `us-central1-a`
- **Status**: ⏳ PROVISIONING (5-8 minutes)
- **Node Configuration**:
  - Machine Type: `e2-medium` (2 vCPUs, 4GB RAM)
  - Initial Nodes: 3
  - Autoscaling: 2-6 nodes
  - Disk Size: 50GB standard persistent disk
- **Features**:
  - ✅ Workload Identity enabled (`botpproject.svc.id.goog`)
  - ✅ VPC-native (IP aliasing)
  - ✅ Auto-repair enabled
  - ✅ Auto-upgrade enabled
  - ✅ Default network

---

## 📋 Next Steps

### 1. Wait for Cluster to be Ready

Check cluster status:
```bash
gcloud container clusters describe chatbot-rag-gke \
  --project=botpproject \
  --zone=us-central1-a \
  --format="value(status)"
```

**Expected Output**: `RUNNING`

---

### 2. Get Cluster Credentials

Once the cluster is RUNNING, get credentials:
```bash
gcloud container clusters get-credentials chatbot-rag-gke \
  --project=botpproject \
  --zone=us-central1-a
```

Verify kubectl access:
```bash
kubectl get nodes
```

**Expected Output**: 3 nodes in Ready state

---

### 3. Create Kubernetes Service Accounts

Apply the service account manifest:
```bash
cd c:\Users\RAMGAUR\OneDrive - Capgemini\Desktop\Week\week3\week3_btoproject_cloudrun_full
kubectl apply -f k8s/service-account.yaml
```

Verify:
```bash
kubectl get serviceaccounts
```

**Expected Output**:
```
NAME               SECRETS   AGE
rag-backend-sa     0         <time>
rag-frontend-sa    0         <time>
```

---

### 4. Create ConfigMaps and Secrets

#### Create Redis ConfigMap
```bash
kubectl apply -f k8s/backend-deployment.yaml --dry-run=client -o yaml | grep -A 5 "kind: ConfigMap" | kubectl apply -f -
```

#### Create ConfigMap for Environment Variables
```bash
kubectl apply -f k8s/configmap.yaml
```

#### Create Secrets (if not using Secret Manager)
```bash
# Redis password (if needed)
kubectl create secret generic redis-secret \
  --from-literal=password=""

# SendGrid API Key (optional)
kubectl create secret generic sendgrid-secret \
  --from-literal=api-key="YOUR_SENDGRID_KEY"
```

---

### 5. Build and Push Docker Images

#### Authenticate Docker to Artifact Registry
```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

#### Build and Push Backend Image
```bash
# Build
docker build -t us-central1-docker.pkg.dev/botpproject/rag-service/backend:latest .

# Push
docker push us-central1-docker.pkg.dev/botpproject/rag-service/backend:latest
```

#### Build and Push Frontend Image
```bash
# Build
docker build -t us-central1-docker.pkg.dev/botpproject/rag-service/frontend:latest \
  -f frontend/Dockerfile frontend/

# Push
docker push us-central1-docker.pkg.dev/botpproject/rag-service/frontend:latest
```

---

### 6. Deploy to GKE

#### Deploy Backend
```bash
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
```

#### Deploy Frontend
```bash
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml
```

#### Deploy Ingress (Optional)
```bash
kubectl apply -f k8s/ingress.yaml
```

---

### 7. Verify Deployment

#### Check Pod Status
```bash
kubectl get pods
```

**Expected**: All pods in `Running` state

#### Check Services
```bash
kubectl get services
```

**Expected**: Services with external IPs assigned

#### Check Logs
```bash
# Backend logs
kubectl logs -l app=rag-backend --tail=50

# Frontend logs
kubectl logs -l app=rag-frontend --tail=50
```

---

### 8. Test the Application

#### Get External IP
```bash
kubectl get service rag-backend -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

#### Test Health Endpoint
```bash
export BACKEND_IP=$(kubectl get service rag-backend -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl http://$BACKEND_IP:8080/health
```

**Expected Response**:
```json
{"status": "healthy"}
```

---

## 🔧 Cluster Monitoring

### Check Cluster Status
```bash
gcloud container clusters describe chatbot-rag-gke \
  --project=botpproject \
  --zone=us-central1-a
```

### Monitor Cluster Operations
```bash
gcloud container operations list \
  --project=botpproject \
  --filter="targetLink~chatbot-rag-gke"
```

### View Cluster Logs
```bash
gcloud logging read "resource.type=k8s_cluster AND resource.labels.cluster_name=chatbot-rag-gke" \
  --project=botpproject \
  --limit=50 \
  --format=json
```

---

## 📊 Resource Summary

| Resource | Name/Email | Status | Action |
|----------|-----------|--------|--------|
| GKE Cluster | `chatbot-rag-gke` | ⏳ Provisioning | Wait 5-8 mins |
| Backend SA | `chatbot-rag-backend@botpproject.iam.gserviceaccount.com` | ✅ Created | Ready |
| Frontend SA | `chatbot-rag-frontend@botpproject.iam.gserviceaccount.com` | ✅ Created | Ready |
| WI Backend | `rag-backend-sa` → Backend SA | ✅ Bound | Ready |
| WI Frontend | `rag-frontend-sa` → Frontend SA | ✅ Bound | Ready |
| IAM Permissions | Backend SA | ✅ Granted | 7 roles |
| Docker Images | Backend & Frontend | ❌ Not Built | **BUILD NEXT** |
| K8s Resources | ConfigMaps, Deployments | ❌ Not Applied | Apply after cluster ready |

---

## ⚠️ Important Notes

1. **Cluster Provisioning**: The GKE cluster is currently being created. This takes approximately 5-8 minutes.

2. **Workload Identity**: Already configured. Once K8s service accounts are created in the cluster, they will automatically have access to GCP resources.

3. **Network Access**: The cluster is in the `default` VPC, which has access to:
   - ✅ Redis Memorystore (10.200.18.59)
   - ✅ Internet (for pulling images, accessing external APIs)

4. **Cost Optimization**: Using `e2-medium` instances with autoscaling (2-6 nodes) to stay within free tier limits.

5. **Security**: All sensitive data should be stored in Secret Manager, not in ConfigMaps or environment variables.

---

## 🚀 Quick Start After Cluster is Ready

Run these commands in sequence:

```bash
# 1. Get credentials
gcloud container clusters get-credentials chatbot-rag-gke --project=botpproject --zone=us-central1-a

# 2. Verify cluster
kubectl get nodes

# 3. Create K8s service accounts
kubectl apply -f k8s/service-account.yaml

# 4. Create ConfigMaps
kubectl apply -f k8s/configmap.yaml

# 5. Build and push images (see step 5 above for details)

# 6. Deploy applications
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml

# 7. Check status
kubectl get pods
kubectl get services

# 8. Get external IP
kubectl get service rag-backend -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

---

## 📞 Support Commands

### Delete and Recreate Cluster (if needed)
```bash
gcloud container clusters delete chatbot-rag-gke \
  --project=botpproject \
  --zone=us-central1-a \
  --quiet
```

### Scale Nodes
```bash
gcloud container clusters resize chatbot-rag-gke \
  --project=botpproject \
  --zone=us-central1-a \
  --num-nodes=5
```

### Update Cluster
```bash
gcloud container clusters update chatbot-rag-gke \
  --project=botpproject \
  --zone=us-central1-a \
  --enable-autoscaling \
  --min-nodes=2 \
  --max-nodes=8
```

---

**Creation Date**: March 7, 2026  
**Next Review**: After cluster is RUNNING (check in 5-8 minutes)
