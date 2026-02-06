# Cloud Run Deployment Guide

## Architecture: Separate Frontend & Backend Services

This Terraform configuration deploys **TWO separate Cloud Run services**:

### 1. **Backend Service** (chatbot-rag-backend)
- **Container**: FastAPI Python application
- **Port**: 8080
- **Resources**: 2 CPU, 2GB RAM
- **Auto-scaling**: 1-10 instances
- **Service Account**: chatbot-rag-backend@
- **Permissions**: 
  - Vertex AI access
  - Cloud Storage access
  - Secret Manager access
  - Redis access via VPC connector
- **Endpoints**: `/api/v1/*` (REST API)

### 2. **Frontend Service** (chatbot-rag-frontend)
- **Container**: Angular app with nginx
- **Port**: 80
- **Resources**: 1 CPU, 512MB RAM
- **Auto-scaling**: 0-5 instances (scales to zero)
- **Service Account**: chatbot-rag-frontend@
- **Permissions**: Minimal (logging only)
- **Serves**: Static SPA, proxies API calls to backend

---

## Deployment Architecture

```
User Browser
    ↓
Frontend Cloud Run Service (chatbot-rag-frontend)
  ├── Static Angular App (nginx)
  └── API calls → Backend URL
          ↓
Backend Cloud Run Service (chatbot-rag-backend)
  ├── FastAPI REST API
  ├── VPC Connector → Redis (Cloud Memorystore)
  ├── Vertex AI (Gemini, Embeddings, Vector Search)
  ├── Cloud Storage (Document storage)
  ├── Firestore (Metadata & Analytics)
  └── Secret Manager (JWT, OAuth secrets)
```

---

## Key Features

### Separate Services Benefits:
1. **Independent Scaling**: Frontend and backend scale independently
2. **Different Resource Limits**: Frontend needs less CPU/RAM
3. **Cost Optimization**: Frontend can scale to zero when idle
4. **Security Separation**: Different service accounts with minimal permissions
5. **Deployment Independence**: Update frontend without touching backend

### Networking:
- **VPC Connector**: Backend uses VPC connector to access Redis in private network
- **Public URLs**: Both services get public HTTPS URLs
- **CORS**: Backend configured to accept requests from frontend URL

### Security:
- **Service Accounts**: Separate least-privilege accounts
- **Secrets**: JWT and OAuth stored in Secret Manager
- **IAM**: Backend has AI/Storage access, Frontend has minimal permissions

---

## Deployment Steps

### 1. Initialize Terraform
```bash
cd infra/terraform
terraform init
```

### 2. Review Plan
```bash
terraform plan -out=cloudrun.tfplan
```

### 3. Build and Push Container Images

**Backend:**
```bash
cd ../..
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/btoproject-486405/chatbot-rag-images/backend:latest \
  .
```

**Frontend:**
```bash
cd frontend

# Update environment.prod.ts with backend URL first
# You'll need to deploy backend first, get URL, then update and deploy frontend

gcloud builds submit \
  --tag us-central1-docker.pkg.dev/btoproject-486405/chatbot-rag-images/frontend:latest \
  -f Dockerfile \
  .
```

### 4. Apply Terraform
```bash
cd ../infra/terraform
terraform apply cloudrun.tfplan
```

### 5. Update Frontend with Backend URL
```bash
# Get backend URL
BACKEND_URL=$(terraform output -raw backend_url)

# Update frontend environment
cd ../../frontend/src/environments
# Edit environment.prod.ts:
# apiUrl: '$BACKEND_URL/api/v1'

# Rebuild and redeploy frontend
cd ../..
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/btoproject-486405/chatbot-rag-images/frontend:latest \
  -f Dockerfile .

# Redeploy frontend service
gcloud run services update chatbot-rag-frontend \
  --region us-central1 \
  --image us-central1-docker.pkg.dev/btoproject-486405/chatbot-rag-images/frontend:latest
```

### 6. Configure OAuth
```bash
# Get frontend URL
FRONTEND_URL=$(terraform output -raw frontend_url)

# Add to Google OAuth Console:
# Authorized JavaScript origins: $FRONTEND_URL
# Authorized redirect URIs: $FRONTEND_URL/login

# Store OAuth credentials
echo -n "YOUR_CLIENT_ID" | gcloud secrets create google-oauth-client-id --data-file=-
echo -n "YOUR_CLIENT_SECRET" | gcloud secrets create google-oauth-client-secret --data-file=-
```

---

## Environment Variables

### Backend Service:
- `PROJECT_ID`: btoproject-486405
- `REGION`: us-central1
- `VERTEX_LOCATION`: us-central1
- `MODEL_VARIANT`: gemini-2.0-flash-001
- `EMBEDDING_MODEL`: text-embedding-004
- `REDIS_HOST`: Auto-configured from Redis instance
- `REDIS_PORT`: Auto-configured from Redis instance
- `GCS_BUCKET`: Auto-created bucket name
- `FIRESTORE_COLLECTION`: rag_chunks
- `USE_FIRESTORE`: true
- `LOG_LEVEL`: INFO
- `MAX_TOKENS`: 8000

### Frontend Service:
- `API_URL`: Auto-configured to backend URL
- `ENVIRONMENT`: production

---

## Monitoring & Logs

### Backend Logs:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=chatbot-rag-backend" \
  --limit 50 --format json
```

### Frontend Logs:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=chatbot-rag-frontend" \
  --limit 50 --format json
```

### Metrics Dashboard:
```bash
# Navigate to Cloud Console → Cloud Run
# Select each service to view metrics
```

---

## Cost Estimation

### Backend:
- **Minimum**: 1 instance always running
- **CPU**: 2 vCPU × $0.00002400/vCPU-second
- **Memory**: 2GB × $0.00000250/GB-second
- **Requests**: $0.40 per million requests
- **Estimated**: ~$50-100/month (depending on usage)

### Frontend:
- **Minimum**: 0 instances (scales to zero)
- **CPU**: 1 vCPU × $0.00002400/vCPU-second
- **Memory**: 512MB × $0.00000250/GB-second
- **Requests**: $0.40 per million requests
- **Estimated**: ~$10-30/month (depending on usage)

### Redis:
- **Standard HA**: 5GB memory
- **Estimated**: ~$170/month

**Total Monthly Cost**: ~$230-300/month

---

## Comparison: Cloud Run vs GKE

| Aspect | Cloud Run (2 Services) | GKE (2 Deployments) |
|--------|------------------------|---------------------|
| **Infrastructure** | Serverless, managed | Kubernetes cluster |
| **Scaling** | Automatic, per service | Manual HPA configuration |
| **Cost** | Pay per use | Fixed cluster + node costs |
| **Setup Time** | 30 minutes | 2 hours |
| **Complexity** | Low | High |
| **Best For** | Dev, staging, low traffic | Production, high traffic, 99.9% SLA |
| **Monthly Cost** | ~$230-300 | ~$500-800 |

---

## Terraform Resources Created

This configuration creates:
1. ✅ **2 Cloud Run Services** (frontend, backend)
2. ✅ **2 Service Accounts** (separate permissions)
3. ✅ **VPC Connector** (for Redis access)
4. ✅ **Cloud Memorystore Redis** (Standard HA, 5GB)
5. ✅ **Artifact Registry** (Docker repository)
6. ✅ **Secret Manager Secrets** (JWT, OAuth)
7. ✅ **GCS Bucket** (Document storage)
8. ✅ **IAM Bindings** (Least-privilege permissions)

---

## Troubleshooting

### Issue: Frontend can't reach backend
**Solution**: Check CORS configuration in backend `main_enhanced.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chatbot-rag-frontend-xyz.run.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Issue: Backend can't connect to Redis
**Solution**: Verify VPC connector is attached:
```bash
gcloud run services describe chatbot-rag-backend \
  --region us-central1 \
  --format="value(spec.template.metadata.annotations.'run.googleapis.com/vpc-access-connector')"
```

### Issue: 502 Bad Gateway
**Solution**: Check backend health endpoint:
```bash
curl https://chatbot-rag-backend-xyz.run.app/health
```

### Issue: OAuth errors
**Solution**: Verify OAuth credentials and authorized URLs in Google Cloud Console

---

## Cleanup

To destroy all resources:
```bash
cd infra/terraform
terraform destroy
```

**Warning**: This will delete:
- Cloud Run services
- Redis instance (data loss!)
- Container images
- All configuration

---

## Next Steps

1. **Deploy to Cloud Run** using this Terraform
2. **Configure custom domain** (optional)
3. **Set up Cloud CDN** for frontend (optional)
4. **Configure monitoring alerts**
5. **Enable Cloud Armor** for DDoS protection (optional)

---

**Last Updated**: February 5, 2026  
**Status**: Ready for deployment ✅
