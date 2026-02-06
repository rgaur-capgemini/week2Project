# ChatBot RAG Application - Operations Runbook

## Table of Contents
1. [Deployment Guide](#deployment-guide)
2. [Monitoring and Alerts](#monitoring-and-alerts)
3. [Troubleshooting](#troubleshooting)
4. [Scaling Operations](#scaling-operations)
5. [Backup and Recovery](#backup-and-recovery)
6. [Security Operations](#security-operations)

---

## Deployment Guide

### Prerequisites
- GCP Project: `btoproject-486405`
- GCloud CLI installed and authenticated
- Kubectl installed
- Terraform >= 1.6.0

### Initial Infrastructure Setup

```bash
# 1. Navigate to terraform directory
cd infra/terraform

# 2. Initialize Terraform
terraform init

# 3. Review the plan
terraform plan

# 4. Apply infrastructure
terraform apply

# 5. Configure kubectl
gcloud container clusters get-credentials chatbot-rag-gke \
  --zone=us-central1-a \
  --project=btoproject-486405
```

### Deploy Application

```bash
# 1. Update ConfigMap with Redis host from Terraform output
REDIS_HOST=$(terraform output -raw redis_host)
kubectl create configmap app-config \
  --from-literal=redis_host=$REDIS_HOST \
  --from-literal=redis_port=6379 \
  --dry-run=client -o yaml | kubectl apply -f -

# 2. Create secrets
kubectl create secret generic app-secrets \
  --from-literal=admin_emails="admin@example.com" \
  --from-literal=google_client_ids="YOUR_CLIENT_ID.apps.googleusercontent.com" \
  --dry-run=client -o yaml | kubectl apply -f -

# 3. Apply Kubernetes manifests
kubectl apply -f infra/kubernetes/deployment.yaml

# 4. Verify deployment
kubectl get pods
kubectl get services
kubectl get ingress
```

### Continuous Deployment via Cloud Build

```bash
# Trigger manual build
gcloud builds submit --config=ci/cloudbuild-gke.yaml

# Setup automated trigger
gcloud builds triggers create github \
  --repo-name=chatbot-rag \
  --repo-owner=YOUR_ORG \
  --branch-pattern="^main$" \
  --build-config=ci/cloudbuild-gke.yaml
```

---

## Monitoring and Alerts

### Key Metrics to Monitor

1. **Application Health**
   - Pod health: `kubectl get pods -w`
   - Service endpoints: `kubectl get endpoints`
   - Ingress status: `kubectl describe ingress chatbot-rag-ingress`

2. **Resource Utilization**
   ```bash
   # CPU and Memory usage
   kubectl top pods
   kubectl top nodes
   
   # HPA status
   kubectl get hpa
   ```

3. **Application Metrics**
   - Query latency (P50, P95, P99)
   - Token usage and cost
   - Error rates
   - Active sessions

### Access Logs

```bash
# Backend logs
kubectl logs -l component=backend --tail=100 -f

# Frontend logs
kubectl logs -l component=frontend --tail=100 -f

# Cloud Logging query
gcloud logging read "resource.type=k8s_container AND resource.labels.cluster_name=chatbot-rag-gke" \
  --limit 50 --format json
```

### Monitoring Dashboard

Access Google Cloud Console:
- **GKE Workloads**: https://console.cloud.google.com/kubernetes/workload
- **Cloud Monitoring**: https://console.cloud.google.com/monitoring
- **Cloud Logging**: https://console.cloud.google.com/logs

### Setting Up Alerts

```bash
# Create alert for high error rate
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s
```

---

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name>

# Check events
kubectl get events --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name> --previous

# Common issues:
# 1. Image pull errors - verify Artifact Registry permissions
# 2. Resource limits - check node capacity
# 3. ConfigMap/Secret missing - verify secrets exist
```

### Application Errors

```bash
# Check application logs
kubectl logs -l app=chatbot-rag --tail=200

# Check readiness probe failures
kubectl describe pod <pod-name> | grep -A 10 "Readiness"

# Test backend health endpoint
kubectl exec -it <backend-pod> -- curl localhost:8080/health
```

### Redis Connection Issues

```bash
# Verify Redis instance
gcloud redis instances describe chatbot-chat-history \
  --region=us-central1

# Test Redis connectivity from pod
kubectl exec -it <backend-pod> -- python -c "
import redis
r = redis.Redis(host='REDIS_HOST', port=6379)
print(r.ping())
"
```

### High Latency

1. Check Vertex AI quota and limits
2. Review recent code changes
3. Check database/Redis performance
4. Analyze Cloud Trace for bottlenecks

```bash
# View traces in Cloud Console
gcloud trace list --limit=20
```

### Out of Memory (OOM)

```bash
# Check resource usage
kubectl top pods

# Increase memory limits
kubectl edit deployment chatbot-rag-backend

# Scale horizontally
kubectl scale deployment chatbot-rag-backend --replicas=5
```

---

## Scaling Operations

### Manual Scaling

```bash
# Scale backend
kubectl scale deployment chatbot-rag-backend --replicas=5

# Scale frontend
kubectl scale deployment chatbot-rag-frontend --replicas=3
```

### Horizontal Pod Autoscaling

HPA is configured automatically. Monitor with:
```bash
kubectl get hpa
kubectl describe hpa chatbot-rag-backend-hpa
```

### Node Pool Scaling

```bash
# Manual node scaling
gcloud container clusters resize chatbot-rag-gke \
  --node-pool=primary-node-pool \
  --num-nodes=5 \
  --zone=us-central1-a
```

### Redis Scaling

```bash
# Upgrade Redis tier
gcloud redis instances update chatbot-chat-history \
  --size=10 \
  --region=us-central1
```

---

## Backup and Recovery

### Firestore Backup

```bash
# Export Firestore data
gcloud firestore export gs://btoproject-486405-backups/$(date +%Y%m%d)

# Restore from backup
gcloud firestore import gs://btoproject-486405-backups/YYYYMMDD
```

### GCS Document Backup

```bash
# Sync to backup bucket
gsutil -m rsync -r \
  gs://btoproject-486405-rag-documents \
  gs://btoproject-486405-rag-documents-backup
```

### Disaster Recovery Plan

1. **Infrastructure**: Terraform state stored in GCS with versioning
2. **Application**: Container images in Artifact Registry (retained)
3. **Data**: 
   - Firestore: Automated daily backups
   - GCS: Cross-region replication
   - Redis: Automated snapshots (Standard HA tier)

### Recovery Procedure

```bash
# 1. Restore infrastructure
cd infra/terraform
terraform apply

# 2. Restore data
gcloud firestore import gs://btoproject-486405-backups/LATEST

# 3. Redeploy application
kubectl apply -f infra/kubernetes/deployment.yaml

# 4. Verify
kubectl get pods
curl http://INGRESS_IP/health
```

---

## Security Operations

### Certificate Management

```bash
# Check SSL certificate status
kubectl describe managedcertificate chatbot-rag-cert

# Renew certificate (automatic with Google-managed certs)
# Verify in Cloud Console
```

### Secret Rotation

```bash
# Rotate JWT secret
gcloud secrets versions add chatbot-jwt-secret --data-file=new-secret.txt

# Update application secrets
kubectl create secret generic app-secrets \
  --from-literal=admin_emails="new-admin@example.com" \
  --dry-run=client -o yaml | kubectl apply -f -

# Rolling restart to pick up new secrets
kubectl rollout restart deployment/chatbot-rag-backend
```

### Audit Logs

```bash
# View audit logs
gcloud logging read "protoPayload.@type=type.googleapis.com/google.cloud.audit.AuditLog" \
  --limit=50 \
  --format=json

# Filter for security events
gcloud logging read "protoPayload.methodName=~'.*delete.*'" \
  --limit=20
```

### Security Scanning

```bash
# Scan container images
gcloud artifacts docker images scan IMAGE_NAME \
  --location=us-central1

# View vulnerability report
gcloud artifacts docker images list-tags IMAGE_NAME \
  --show-occurrences
```

---

## Performance Tuning

### Optimize Query Performance

1. **Enable caching** for frequently accessed documents
2. **Tune chunking parameters** for better retrieval
3. **Adjust top_k** parameter based on accuracy needs
4. **Use reranking** selectively for critical queries

### Database Optimization

```bash
# Check Firestore index status
gcloud firestore indexes list

# Create composite indexes if needed
gcloud firestore indexes composite create \
  --collection-group=analytics_metrics \
  --field-config field-path=user_email,order=ascending \
  --field-config field-path=timestamp,order=descending
```

### Cost Optimization

1. Review Vertex AI usage and adjust models
2. Monitor token consumption via analytics dashboard
3. Use committed use discounts for predictable workloads
4. Enable preemptible nodes for non-critical workloads

---

## Contact and Escalation

### On-Call Engineer
- Primary: DevOps Team
- Backup: Platform Engineering

### Escalation Path
1. **L1**: Application errors, performance issues
2. **L2**: Infrastructure problems, scaling issues
3. **L3**: Architecture changes, major incidents

### External Dependencies
- **Google Cloud Support**: https://cloud.google.com/support
- **Vertex AI Issues**: Check status at https://status.cloud.google.com

---

*Last Updated: February 2026*
*Version: 1.0*
