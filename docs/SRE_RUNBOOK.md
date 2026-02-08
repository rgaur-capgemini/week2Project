# SRE Runbook - RAG Chatbot Production System

## Emergency Contacts
- **On-Call Engineer**: PagerDuty rotation
- **Escalation**: SRE Lead / Engineering Manager
- **GCP Support**: Priority Support (P1/P2)

## System Overview

### Architecture
```
Users → Load Balancer → GKE (Frontend/Backend) → Vertex AI
                                ↓
                           Redis (History/Analytics)
                                ↓
                           GCS (Documents) + Firestore (Metadata)
```

### Critical Components
1. **GKE Cluster**: `rag-chatbot-cluster`
2. **Backend**: 3-20 replicas (HPA enabled)
3. **Frontend**: 2-10 replicas (HPA enabled)
4. **Redis Memorystore**: HA configuration
5. **Vertex AI**: Vector Search + Gemini

### SLOs (Service Level Objectives)
- **Availability**: 99.9% (< 44 minutes downtime/month)
- **Latency**: p95 < 2 seconds for /query
- **Error Rate**: < 1%
- **Data Loss**: Zero (RPO = 0)

---

## Common Incidents & Resolutions

### 1. High Error Rate (5xx)

**Symptoms**:
- Error rate > 5%
- Users reporting failures
- Alerts firing

**Investigation**:
```bash
# Check pod status
kubectl get pods -l app=rag-backend

# Check logs for errors
kubectl logs -l app=rag-backend --tail=500 | grep ERROR

# Check recent deployments
kubectl rollout history deployment/rag-backend
```

**Common Causes**:
- Recent bad deployment
- Vertex AI API errors
- Redis connection issues
- Resource exhaustion

**Resolution**:
```bash
# Rollback if recent deployment
kubectl rollout undo deployment/rag-backend

# Scale up if resource issue
kubectl scale deployment rag-backend --replicas=10

# Restart pods if connection issue
kubectl rollout restart deployment/rag-backend
```

**Escalation**: If persists > 15 minutes, escalate to on-call

---

### 2. High Latency (p95 > 5s)

**Symptoms**:
- Slow response times
- Timeouts
- User complaints

**Investigation**:
```bash
# Check HPA status
kubectl get hpa

# Check resource usage
kubectl top pods -l app=rag-backend

# Check Vertex AI latency in logs
kubectl logs -l app=rag-backend | grep "duration"
```

**Common Causes**:
- Under-scaled (not enough replicas)
- Vertex AI throttling
- Large document ingestion
- Redis performance issues

**Resolution**:
```bash
# Immediate: Scale up
kubectl scale deployment rag-backend --replicas=15

# Check Vertex AI quotas
gcloud services quotas list \
  --service=aiplatform.googleapis.com \
  --filter="limit_name:MatchingEngine"

# Request quota increase if needed
```

**Prevention**:
- Enable aggressive HPA scaling
- Monitor Vertex AI quotas
- Implement request queueing

---

### 3. Authentication Failures

**Symptoms**:
- 401 Unauthorized errors
- Users can't log in
- "Invalid token" errors

**Investigation**:
```bash
# Check if secrets are accessible
gcloud secrets versions access latest \
  --secret=oauth-client-id \
  --project=$PROJECT_ID

# Check service account permissions
kubectl describe serviceaccount rag-backend

# Check Workload Identity binding
gcloud iam service-accounts get-iam-policy \
  rag-backend-sa@$PROJECT_ID.iam.gserviceaccount.com
```

**Common Causes**:
- Expired OAuth credentials
- Secret Manager access denied
- Workload Identity misconfiguration
- Clock skew (JWT validation)

**Resolution**:
```bash
# Verify secrets are correct
gcloud secrets versions access latest --secret=oauth-client-id

# Recreate Workload Identity binding if broken
gcloud iam service-accounts add-iam-policy-binding \
  rag-backend-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:$PROJECT_ID.svc.id.goog[default/rag-backend]"

# Restart pods to pick up changes
kubectl rollout restart deployment/rag-backend
```

**Escalation**: Contact security team if OAuth credentials compromised

---

### 4. Redis Connection Failures

**Symptoms**:
- Chat history not saving
- Analytics not recording
- "Redis connection failed" errors

**Investigation**:
```bash
# Check Redis instance status
gcloud redis instances describe rag-chatbot-redis \
  --region=$REGION

# Test connectivity from GKE
kubectl run redis-test --rm -it --image=redis:7 -- \
  redis-cli -h $REDIS_HOST ping

# Check application logs
kubectl logs -l app=rag-backend | grep -i redis
```

**Common Causes**:
- Redis instance down
- Network connectivity issue
- Connection pool exhaustion
- Redis memory full

**Resolution**:
```bash
# Check Redis memory usage
gcloud redis instances describe rag-chatbot-redis \
  --region=$REGION \
  --format="value(memorySizeGb,currentLocationId)"

# If memory issue, increase size or clear old data
# Restart Redis (causes brief downtime)
gcloud redis instances failover rag-chatbot-redis \
  --region=$REGION \
  --data-protection-mode=limited-data-loss
```

**Mitigation**:
- Application continues working without history
- Analytics degraded but non-critical
- Users won't notice immediate impact

---

### 5. Vertex AI Quota Exceeded

**Symptoms**:
- "Quota exceeded" errors
- 429 rate limit errors
- Queries failing

**Investigation**:
```bash
# Check current quotas
gcloud services quotas list \
  --service=aiplatform.googleapis.com \
  --format="table(limitName,limit,usage)"

# Check rate of API calls
kubectl logs -l app=rag-backend | grep "VertexAI" | wc -l
```

**Resolution**:
```bash
# Request quota increase (immediate, while waiting for approval)
gcloud alpha services quotas update \
  --service=aiplatform.googleapis.com \
  --consumer=projects/$PROJECT_ID \
  --metric=aiplatform.googleapis.com/vertex_ai_requests \
  --value=10000 \
  --justification="Production spike"

# Implement rate limiting
# Add to main.py:
# from slowapi import Limiter
# limiter = Limiter(key_func=get_remote_address)
# app.state.limiter = limiter
```

**Temporary Mitigation**:
- Enable caching for repeat queries
- Batch requests where possible
- Implement queue system

---

### 6. Pod CrashLoopBackOff

**Symptoms**:
- Pods continuously restarting
- Service unavailable
- Critical alerts

**Investigation**:
```bash
# Check pod status
kubectl get pods -l app=rag-backend

# Get pod logs before crash
kubectl logs POD_NAME --previous

# Describe pod for events
kubectl describe pod POD_NAME

# Check resource limits
kubectl describe deployment rag-backend | grep -A 10 Limits
```

**Common Causes**:
- Application startup failure
- Missing environment variables
- Out of memory (OOM)
- Failed health checks

**Resolution**:
```bash
# Check if OOM killed
kubectl describe pod POD_NAME | grep -i oom

# If OOM, increase memory limits
kubectl patch deployment rag-backend -p \
  '{"spec":{"template":{"spec":{"containers":[{"name":"rag-backend","resources":{"limits":{"memory":"8Gi"}}}]}}}}'

# If startup failure, check env vars
kubectl exec -it POD_NAME -- env | sort

# If health check issue, increase timeouts
kubectl patch deployment rag-backend --type='json' -p='[
  {"op":"replace","path":"/spec/template/spec/containers/0/livenessProbe/timeoutSeconds","value":10}
]'
```

---

### 7. Data Loss / Corruption

**Symptoms**:
- Users report missing chat history
- Documents not found
- Inconsistent query results

**Investigation**:
```bash
# Check Redis health
gcloud redis instances describe rag-chatbot-redis --region=$REGION

# Check GCS bucket
gsutil ls gs://$PROJECT_ID-rag-documents/

# Check Firestore
gcloud firestore databases describe --database=rag_chunks

# Verify Vector Index status
gcloud ai indexes list --region=$REGION
```

**Resolution**:
- Redis: Memorystore has automatic backups
- GCS: Object versioning enabled
- Firestore: Point-in-time recovery available

```bash
# Restore Redis from backup (if needed)
# Contact GCP support for Memorystore recovery

# Restore GCS object version
gsutil cp gs://BUCKET/OBJECT#VERSION gs://BUCKET/OBJECT

# Firestore recovery
# Use Cloud Console > Firestore > Import/Export
```

**Prevention**:
- Regular backups (automated)
- Multi-region replication (for critical data)
- Versioning enabled

---

## Monitoring & Alerts

### Key Dashboards

1. **Cloud Console - GKE**: https://console.cloud.google.com/kubernetes
2. **Cloud Monitoring**: Custom dashboard with:
   - Request rate
   - Error rate
   - Latency (p50, p95, p99)
   - Resource utilization
3. **Cloud Trace**: Distributed tracing for slow requests

### Alert Policies

| Alert | Threshold | Severity | Action |
|-------|-----------|----------|--------|
| High error rate | > 5% for 5m | P1 | Page on-call |
| High latency | p95 > 5s for 10m | P2 | Investigate |
| Pod crash | 3+ restarts in 5m | P1 | Page on-call |
| Low replicas | < 2 healthy pods | P1 | Auto-scale + alert |
| Redis down | Connection fail | P1 | Page on-call |
| Disk usage | > 85% | P2 | Expand disk |
| Memory usage | > 90% | P2 | Scale up |

### Setting Up Alerts

```bash
# Create alert policy for high error rate
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s
```

---

## Maintenance Procedures

### Routine Maintenance (Weekly)

```bash
# 1. Check cluster health
gcloud container clusters describe $CLUSTER_NAME \
  --region=$REGION | grep status

# 2. Review resource usage
kubectl top nodes
kubectl top pods --all-namespaces

# 3. Check for security updates
gcloud container get-server-config --region=$REGION

# 4. Review logs for warnings
kubectl logs -l app=rag-backend --since=7d | grep -i warning

# 5. Verify backups
gcloud redis instances describe rag-chatbot-redis \
  --region=$REGION --format="get(persistenceConfig)"
```

### Planned Deployments

**Pre-deployment Checklist**:
- [ ] Code reviewed and approved
- [ ] Tests passing (>70% coverage)
- [ ] Security scans clean
- [ ] Staging environment tested
- [ ] Rollback plan ready
- [ ] Stakeholders notified

**Deployment Process**:
```bash
# 1. Create backup/snapshot
kubectl get all -n default -o yaml > backup-$(date +%Y%m%d).yaml

# 2. Deploy via CI/CD
gcloud builds submit --config=ci/cloudbuild-gke.yaml

# 3. Monitor rollout
kubectl rollout status deployment/rag-backend

# 4. Verify health
curl http://$BACKEND_IP/health
curl http://$BACKEND_IP/readiness

# 5. Monitor errors for 30 minutes
kubectl logs -l app=rag-backend --since=30m | grep ERROR
```

**Rollback Procedure**:
```bash
# Quick rollback
kubectl rollout undo deployment/rag-backend

# Rollback to specific revision
kubectl rollout history deployment/rag-backend
kubectl rollout undo deployment/rag-backend --to-revision=N
```

---

## Performance Tuning

### Optimize Query Latency

1. **Enable Prompt Compression**: Already implemented
2. **Tune HPA**: Adjust scaling thresholds
   ```bash
   kubectl patch hpa rag-backend-hpa -p \
     '{"spec":{"metrics":[{"type":"Resource","resource":{"name":"cpu","target":{"type":"Utilization","averageUtilization":60}}}]}}'
   ```
3. **Increase Vertex AI Batch Size**: Adjust in code
4. **Redis Connection Pooling**: Tune pool size

### Optimize Costs

1. **Use Spot VMs** for non-critical workloads
2. **Enable cluster autoscaling**
   ```bash
   gcloud container clusters update $CLUSTER_NAME \
     --enable-autoscaling \
     --min-nodes=2 --max-nodes=10 \
     --region=$REGION
   ```
3. **Right-size resources**: Review and adjust requests/limits

---

## Security Incident Response

### Suspected Breach

1. **Immediate**: Isolate affected components
   ```bash
   kubectl scale deployment rag-backend --replicas=0
   ```
2. **Rotate all secrets**
   ```bash
   # Generate new secrets
   openssl rand -base64 32 | gcloud secrets versions add jwt-secret --data-file=-
   ```
3. **Review audit logs**
   ```bash
   gcloud logging read "protoPayload.methodName=~'.*'" \
     --limit=1000 \
     --format=json > audit-$(date +%Y%m%d).json
   ```
4. **Contact security team**
5. **Incident report**: Document timeline and actions

---

## Capacity Planning

### Current Capacity
- **Backend**: 3-20 pods (can handle ~10,000 req/hour)
- **Frontend**: 2-10 pods
- **Redis**: 5GB (can store ~500K messages)
- **Vertex AI**: Standard quotas

### Scaling Triggers
- Add nodes when CPU > 70% for > 5 minutes
- Scale pods when requests > 100/minute/pod
- Increase Redis when memory > 80%

### Growth Planning
- Monthly review of usage trends
- Quarterly capacity assessment
- Annual architecture review

---

## Contact & Escalation

### Escalation Path
1. **L1**: On-call engineer (PagerDuty)
2. **L2**: SRE Lead
3. **L3**: Engineering Manager
4. **L4**: GCP Support (for infrastructure)

### External Dependencies
- **GCP Support**: support@google.com
- **Vertex AI Team**: Internal escalation
- **Security Team**: security@company.com

---

**Runbook Version**: 1.0  
**Last Updated**: 2026-02-07  
**Next Review**: 2026-03-07  
**Owner**: SRE Team
