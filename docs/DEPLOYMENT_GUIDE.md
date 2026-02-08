# RAG Chatbot - Complete Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Infrastructure Deployment](#infrastructure-deployment)
4. [Application Deployment](#application-deployment)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Monitoring and Operations](#monitoring-and-operations)

---

## Prerequisites

### Required Tools
- `gcloud` CLI (latest version)
- `terraform` >= 1.6.0
- `kubectl` >= 1.28
- `docker` >= 24.0
- `git`
- Access to GCP project: `btoproject-486405-486604`

### GCP Permissions Required
- Project Owner or Editor
- Kubernetes Engine Admin
- Service Account Admin
- Secret Manager Admin
- Cloud Build Editor

### Environment Variables
```bash
export PROJECT_ID="btoproject-486405-486604"
export PROJECT_NUMBER="382685100652"
export REGION="us-central1"
export ZONE="us-central1-a"
export CLUSTER_NAME="rag-chatbot-cluster"
```

---

## Initial Setup

### 1. Configure OAuth 2.0 Credentials

1. Go to [GCP Console > APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)
2. Create OAuth 2.0 Client ID:
   - Application type: **Web application**
   - Authorized JavaScript origins: `https://your-frontend-domain.com`
   - Authorized redirect URIs: `https://your-frontend-domain.com/callback`
3. Note the **Client ID** and **Client Secret**

### 2. Store Secrets in Secret Manager

```bash
# OAuth Client ID
echo -n "YOUR_CLIENT_ID" | gcloud secrets create oauth-client-id \
  --data-file=- \
  --project=$PROJECT_ID

# OAuth Client Secret  
echo -n "YOUR_CLIENT_SECRET" | gcloud secrets create oauth-client-secret \
  --data-file=- \
  --project=$PROJECT_ID

# JWT Secret (generate random secure string)
openssl rand -base64 32 | gcloud secrets create jwt-secret \
  --data-file=- \
  --project=$PROJECT_ID
```

### 3. Configure Admin Emails

Create an environment variable or secret with admin emails:

```bash
export ADMIN_EMAILS="admin1@company.com,admin2@company.com"

echo -n "$ADMIN_EMAILS" | gcloud secrets create admin-emails \
  --data-file=- \
  --project=$PROJECT_ID
```

### 4. Enable Required APIs

```bash
gcloud services enable \
  container.googleapis.com \
  compute.googleapis.com \
  aiplatform.googleapis.com \
  storage-api.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  redis.googleapis.com \
  --project=$PROJECT_ID
```

---

## Infrastructure Deployment

### 1. Initialize Terraform

```bash
cd infra/terraform

# Create GCS bucket for Terraform state
gsutil mb -p $PROJECT_ID -l $REGION gs://${PROJECT_ID}-terraform-state

# Initialize
terraform init
```

### 2. Review and Apply Infrastructure

```bash
# Review planned changes
terraform plan -var="project_id=$PROJECT_ID"

# Apply infrastructure
terraform apply -var="project_id=$PROJECT_ID" -auto-approve
```

This will create:
- ✅ VPC network with private subnets
- ✅ GKE cluster with 2 node pools (backend, frontend)
- ✅ Redis Memorystore instance
- ✅ Service accounts with Workload Identity
- ✅ GCS buckets
- ✅ IAM bindings

**Deployment time:** ~15-20 minutes

### 3. Get Infrastructure Outputs

```bash
terraform output

# Save outputs for later use
export REDIS_HOST=$(terraform output -raw redis_host)
export REDIS_PORT=$(terraform output -raw redis_port)
export GKE_CLUSTER=$(terraform output -raw gke_cluster_name)
```

---

## Application Deployment

### Option A: Automated CI/CD Pipeline (Recommended)

1. **Trigger Cloud Build**:
```bash
gcloud builds submit \
  --config=ci/cloudbuild-gke.yaml \
  --project=$PROJECT_ID
```

The pipeline will:
- ✅ Build Docker images
- ✅ Run tests (70% coverage requirement)
- ✅ Security scans (dependency check, secrets scan)
- ✅ Generate SBOM
- ✅ Push to GCR
- ✅ Deploy to GKE
- ✅ Run smoke tests

**Pipeline duration:** ~25-30 minutes

### Option B: Manual Deployment

1. **Get GKE Credentials**:
```bash
gcloud container clusters get-credentials $GKE_CLUSTER \
  --region=$REGION \
  --project=$PROJECT_ID
```

2. **Update ConfigMap with Redis IP**:
```bash
kubectl create configmap redis-config \
  --from-literal=host=$REDIS_HOST \
  --from-literal=port=$REDIS_PORT \
  --dry-run=client -o yaml | kubectl apply -f -
```

3. **Deploy Backend**:
```bash
kubectl apply -f k8s/backend-deployment.yaml
```

4. **Deploy Frontend**:
```bash
kubectl apply -f k8s/frontend-deployment.yaml
```

5. **Wait for Rollout**:
```bash
kubectl rollout status deployment/rag-backend
kubectl rollout status deployment/rag-frontend
```

---

## Post-Deployment Verification

### 1. Check Pod Status

```bash
kubectl get pods -l app=rag-backend
kubectl get pods -l app=rag-frontend

# Should show all pods as Running
```

### 2. Get Service External IPs

```bash
export BACKEND_IP=$(kubectl get service rag-backend -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
export FRONTEND_IP=$(kubectl get service rag-frontend -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Backend URL: http://$BACKEND_IP"
echo "Frontend URL: http://$FRONTEND_IP"
```

### 3. Health Checks

```bash
# Backend health
curl http://$BACKEND_IP/health
# Expected: {"status":"healthy","service":"rag-service","version":"3.0.0"}

# Backend readiness
curl http://$BACKEND_IP/readiness
# Expected: {"ready":true,...}

# Test authentication (should fail without token)
curl http://$BACKEND_IP/auth/me
# Expected: 401 Unauthorized
```

### 4. Test Complete Flow

```bash
# 1. Get test documents ready
echo "Test document content" > test.txt

# 2. Login (requires valid Google OAuth token)
# Use frontend or Postman to get access token

# 3. Ingest document
curl -X POST http://$BACKEND_IP/ingest \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "files=@test.txt" \
  -F "question=What is in the document?"

# 4. Query
curl -X POST http://$BACKEND_IP/query \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is in the document?","top_k":5}'

# 5. Check history
curl http://$BACKEND_IP/history/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 6. View analytics (admin only)
curl http://$BACKEND_IP/analytics/overview \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Monitoring and Operations

### View Logs

```bash
# Backend logs
kubectl logs -l app=rag-backend --tail=100 -f

# Frontend logs
kubectl logs -l app=rag-frontend --tail=100 -f

# Cloud Logging
gcloud logging read "resource.type=k8s_container AND resource.labels.container_name=rag-backend" \
  --limit=50 \
  --format=json
```

### Monitoring Dashboard

Access Cloud Console:
- **GKE Workloads**: https://console.cloud.google.com/kubernetes/workload
- **Cloud Monitoring**: https://console.cloud.google.com/monitoring
- **Cloud Trace**: https://console.cloud.google.com/traces

### Key Metrics to Monitor

1. **Availability**
   - Target: 99.9% uptime
   - Monitor: Pod health, service availability

2. **Latency**
   - Target: p95 < 2s for /query endpoint
   - Monitor: Response time metrics

3. **Error Rate**
   - Target: < 1% error rate
   - Monitor: 5xx responses

4. **Resource Usage**
   - CPU: < 70% average
   - Memory: < 80% average
   - Monitor: HPA scaling events

### Scaling

```bash
# Manual scaling
kubectl scale deployment rag-backend --replicas=5

# Check HPA status
kubectl get hpa

# View scaling events
kubectl describe hpa rag-backend-hpa
```

### Update Deployment

```bash
# Update image
kubectl set image deployment/rag-backend \
  rag-backend=gcr.io/$PROJECT_ID/rag-backend:NEW_TAG

# Rollback if needed
kubectl rollout undo deployment/rag-backend
```

---

## Troubleshooting

### Pods Not Starting

```bash
# Check pod events
kubectl describe pod POD_NAME

# Common issues:
# - Image pull errors → Check GCR permissions
# - Crash loop → Check application logs
# - Resource limits → Increase requests/limits
```

### Authentication Errors

```bash
# Verify secrets exist
gcloud secrets list --project=$PROJECT_ID

# Check service account binding
kubectl describe serviceaccount rag-backend

# Verify Workload Identity
gcloud iam service-accounts get-iam-policy \
  rag-backend-sa@$PROJECT_ID.iam.gserviceaccount.com
```

### Redis Connection Issues

```bash
# Verify Redis is accessible from GKE
kubectl run redis-test --rm -it --image=redis:7 -- redis-cli -h $REDIS_HOST ping

# Should return: PONG
```

### High Latency

```bash
# Check Vector Search performance
# Verify index is deployed properly in Vertex AI Console

# Check Gemini API quotas
gcloud services quotas list \
  --service=aiplatform.googleapis.com \
  --filter="aiplatform"

# Scale up if needed
kubectl scale deployment rag-backend --replicas=10
```

---

## Disaster Recovery

### Backup

```bash
# Backup Redis data (if persistence enabled)
# Backup is automatic with Memorystore HA

# Backup configuration
kubectl get all --all-namespaces -o yaml > backup-$(date +%Y%m%d).yaml

# Backup secrets (encrypted)
gcloud secrets list --format="value(name)" | \
  xargs -I {} gcloud secrets versions access latest --secret={}
```

### Restore

```bash
# Restore from backup
kubectl apply -f backup-YYYYMMDD.yaml

# Restore secrets
gcloud secrets create SECRET_NAME --data-file=backup.txt
```

---

## Cost Optimization

### Current Monthly Estimate

- **GKE Cluster**: ~$200-400/month
- **Redis Memorystore**: ~$50-100/month
- **Vertex AI (Vector Search)**: ~$100-300/month
- **Gemini API calls**: Variable (based on usage)
- **Total**: ~$400-800/month

### Optimization Tips

1. **Use Spot VMs for non-critical workloads**
2. **Enable cluster autoscaling**
3. **Set appropriate resource limits**
4. **Use committed use discounts**
5. **Monitor and optimize Vertex AI calls**

---

## Security Checklist

- ✅ OAuth 2.0 authentication enabled
- ✅ JWT token validation
- ✅ RBAC enforced (user vs admin)
- ✅ Secrets in Secret Manager (not hardcoded)
- ✅ Workload Identity configured
- ✅ Network policies applied
- ✅ Private GKE nodes
- ✅ Security scanning in CI/CD
- ✅ PII detection and redaction
- ✅ HTTPS/TLS enabled
- ✅ Audit logging enabled

---

## Support and Escalation

For issues, contact:
- **Email**: sre-team@company.com
- **Slack**: #rag-chatbot-support
- **On-call**: PagerDuty escalation

For GCP support:
- **Support Portal**: https://cloud.google.com/support
- **Priority**: Production P1/P2

---

## Appendix

### Useful Commands

```bash
# Quick health check
kubectl get pods,svc,hpa

# Resource usage
kubectl top pods
kubectl top nodes

# Events
kubectl get events --sort-by='.lastTimestamp'

# Shell into pod
kubectl exec -it POD_NAME -- /bin/bash

# Port forward for local testing
kubectl port-forward svc/rag-backend 8080:80
```

### Configuration Files Location

- Terraform: `infra/terraform/`
- Kubernetes manifests: `k8s/`
- CI/CD pipeline: `ci/cloudbuild-gke.yaml`
- Application code: `app/`
- Frontend: `frontend/`

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-07  
**Next Review Date**: 2026-03-07
