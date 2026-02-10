# Emergency Deployment Rollback Runbook

## 📋 Purpose

Safely rollback a deployment to a previous stable version in case of critical issues, bugs, or performance degradation.

## ⚠️ When to Use

- Critical bugs in production
- Performance degradation > 50%
- Error rate > 5%
- Data corruption issues
- Security vulnerabilities discovered

## 🔑 Prerequisites

### Required Access
- GKE cluster admin access
- `kubectl` configured for production cluster
- Cloud Console access
- Slack access for #incidents channel

### Required Tools
```bash
kubectl version --client  # >= 1.28
gcloud version            # Latest
```

### Required Information
- Target revision number (from rollout history)
- Current deployment status
- Active user count (for impact assessment)

---

## 📝 Pre-Rollback Checklist

- [ ] Notify team in #incidents Slack channel
- [ ] Create incident ticket (JIRA/ServiceNow)
- [ ] Verify you have recent backup (< 1 hour old)
- [ ] Identify target stable version
- [ ] Check active user count
- [ ] Prepare rollback announcement

---

## 🔄 Rollback Procedure

### Step 1: Assess Current Situation

```bash
# Check current deployment status
kubectl get deployments -n default

# Check pod health
kubectl get pods -l app=rag-backend -n default

# Check recent logs for errors
kubectl logs -l app=rag-backend --tail=100 | grep ERROR

# Check error rate in last 5 minutes
gcloud logging read "resource.type=cloud_run_revision severity>=ERROR" \
  --limit 50 --format json | jq length
```

**Decision Point**: If error rate < 5% and no critical issues, consider fix-forward instead of rollback.

---

### Step 2: Create Pre-Rollback Snapshot

```bash
# Set timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup current deployment config
kubectl get deployment rag-backend -o yaml > backup-pre-rollback-${TIMESTAMP}.yaml
kubectl get deployment rag-frontend -o yaml > backup-frontend-pre-rollback-${TIMESTAMP}.yaml

# Backup current service config
kubectl get service rag-backend-service -o yaml > backup-service-${TIMESTAMP}.yaml

# Store in Cloud Storage
gsutil cp backup-*.yaml gs://btoproject-486405-486604-backups/rollback-${TIMESTAMP}/

# Verify upload
gsutil ls gs://btoproject-486405-486604-backups/rollback-${TIMESTAMP}/
```

---

### Step 3: Identify Target Revision

```bash
# View rollout history for backend
kubectl rollout history deployment/rag-backend

# View specific revision details
kubectl rollout history deployment/rag-backend --revision=<REVISION_NUMBER>

# Example output:
# REVISION  CHANGE-CAUSE
# 1         Initial deployment
# 2         Updated to v2.0.1
# 3         Updated to v2.0.2 (CURRENT - BAD)
# 4         Hotfix for auth issue
```

**Identify**: The last known good revision (typically REVISION - 1, unless that was also bad).

---

### Step 4: Notify Stakeholders

**Slack Message Template**:
```
🚨 PRODUCTION ROLLBACK IN PROGRESS 🚨

System: RAG Chatbot Backend
Action: Rolling back from v2.0.2 to v2.0.1
Reason: [Critical bug/High error rate/Performance degradation]
ETA: 5-10 minutes
Incident Ticket: INC-12345

Current Status: Preparing rollback
Expected Impact: Brief service interruption (< 30s)

Updates will be posted here every 2 minutes.
```

---

### Step 5: Execute Rollback - Backend

```bash
# Rollback to previous revision
kubectl rollout undo deployment/rag-backend

# OR rollback to specific revision
kubectl rollout undo deployment/rag-backend --to-revision=2

# Monitor rollback progress
kubectl rollout status deployment/rag-backend --watch

# Expected output:
# Waiting for deployment "rag-backend" rollout to finish: 1 out of 3 new replicas have been updated...
# Waiting for deployment "rag-backend" rollout to finish: 2 out of 3 new replicas have been updated...
# deployment "rag-backend" successfully rolled out
```

**This should take 2-5 minutes depending on HPA and pod startup time.**

---

### Step 6: Execute Rollback - Frontend (if needed)

```bash
# Check if frontend also needs rollback
kubectl rollout history deployment/rag-frontend

# Rollback frontend
kubectl rollout undo deployment/rag-frontend

# Monitor progress
kubectl rollout status deployment/rag-frontend --watch
```

---

### Step 7: Verification

#### 7.1 Check Pod Status
```bash
# Verify all pods are running
kubectl get pods -l app=rag-backend

# Expected: All pods in Running state, READY 1/1

# Check pod logs for errors
kubectl logs -l app=rag-backend --tail=50 --since=2m
```

#### 7.2 Health Checks
```bash
# Get service URL
SERVICE_URL=$(kubectl get service rag-backend-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Health check
curl http://${SERVICE_URL}/health

# Expected: {"status": "healthy"}

# Readiness check
curl http://${SERVICE_URL}/readiness

# Expected: {"status": "ready", "dependencies": {...}}
```

#### 7.3 Smoke Tests
```bash
# Test query endpoint
curl -X POST http://${SERVICE_URL}/query \
  -H "Content-Type: application/json" \
  -d '{"question":"What is RAG?","top_k":3}'

# Expected: JSON response with answer

# Test ingest endpoint (if applicable)
curl -X POST http://${SERVICE_URL}/ingest \
  -F "files=@test-document.pdf"

# Expected: 200 OK with chunk IDs
```

#### 7.4 Monitor Error Rate
```bash
# Check error rate in last 5 minutes
gcloud logging read "resource.type=k8s_container \
  resource.labels.namespace_name=default \
  severity>=ERROR" \
  --limit 100 \
  --format json \
  --freshness=5m | jq length

# Expected: < 5 errors
```

#### 7.5 Check Performance Metrics
Navigate to Cloud Console:
- **Monitoring > Dashboards > RAG Backend**
- Check:
  - Request latency (p95 < 2s)
  - Error rate (< 1%)
  - Request throughput (matches baseline)

---

### Step 8: Update Stakeholders

**Slack Success Message**:
```
✅ ROLLBACK COMPLETED SUCCESSFULLY

System: RAG Chatbot Backend
Action: Rolled back to v2.0.1 (revision 2)
Duration: 6 minutes
Current Status: ✅ HEALTHY

Verification Results:
✅ All pods running (3/3)
✅ Health checks passing
✅ Error rate: 0.3% (normal)
✅ Latency: p95 = 1.2s (good)
✅ Smoke tests passing

Next Steps:
- Monitor for next 30 minutes
- Root cause analysis scheduled
- Fix-forward plan to be created

Incident Ticket: INC-12345
```

---

## 🔧 Troubleshooting

### Issue: Rollback Stuck (Pods not starting)

```bash
# Check pod events
kubectl describe pod <POD_NAME>

# Check resource constraints
kubectl top nodes
kubectl top pods

# Check for image pull errors
kubectl get events --sort-by='.lastTimestamp' | grep Pull

# Solution: Scale up nodes if resource constrained
gcloud container clusters resize rag-chatbot-cluster \
  --num-nodes 5 \
  --region us-central1
```

### Issue: Rollback Completed but Still Seeing Errors

```bash
# Check if error is from old pods still terminating
kubectl get pods -l app=rag-backend -o wide

# Force delete stuck pods
kubectl delete pod <POD_NAME> --force --grace-period=0

# Check if error is from configuration (not code)
kubectl get configmap
kubectl get secrets

# Verify correct ConfigMap is applied
kubectl describe configmap rag-config
```

### Issue: Database Migration Compatibility

```bash
# If rollback fails due to DB schema changes, may need to rollback DB
# Check Firestore collections for schema changes
gcloud firestore databases describe --database=rag_chunks

# For Redis, check for incompatible data structures
# Connect to Redis
kubectl port-forward <REDIS_POD> 6379:6379
redis-cli -h localhost

# Check key patterns
KEYS *

# If incompatible, may need to flush and reseed
# CAUTION: This deletes all Redis data
FLUSHDB
```

---

## ↩️ Rollback the Rollback (Roll Forward)

If the rollback itself caused issues:

```bash
# Roll forward to the version before rollback
kubectl rollout undo deployment/rag-backend

# Or to specific good revision
kubectl rollout undo deployment/rag-backend --to-revision=3
```

---

## 📊 Post-Rollback Actions

### Immediate (0-30 minutes)
- [ ] Monitor error rates
- [ ] Monitor latency metrics
- [ ] Monitor user reports in support channels
- [ ] Keep team notified of status

### Short-term (1-4 hours)
- [ ] Complete incident report
- [ ] Schedule post-mortem meeting (within 24h)
- [ ] Identify root cause
- [ ] Create fix-forward plan
- [ ] Update test coverage to prevent recurrence

### Long-term (1-7 days)
- [ ] Conduct post-mortem
- [ ] Implement preventive measures
- [ ] Update deployment process if needed
- [ ] Share learnings with team
- [ ] Update runbooks based on lessons learned

---

## 📝 Incident Log Template

```markdown
## Incident: [INC-12345] Rollback to v2.0.1

**Date**: 2026-02-10 14:30 UTC
**Duration**: 6 minutes
**Severity**: P1 (Critical)
**Impact**: Brief service degradation

### Timeline
- 14:24 - Issue detected (error rate spike to 15%)
- 14:26 - Incident declared, rollback decision made
- 14:28 - Pre-rollback snapshot created
- 14:30 - Rollback initiated
- 14:36 - Rollback completed, verification successful
- 14:40 - Monitoring confirmed stable
- 14:45 - Incident closed

### Root Cause
[TBD during post-mortem]

### Actions Taken
1. Created pre-rollback snapshot
2. Rolled back backend deployment to revision 2
3. Verified health checks
4. Monitored for 30 minutes

### Preventive Actions
[TBD during post-mortem]
```

---

## 🔗 Related Documentation

- [SRE Runbook](../SRE_RUNBOOK.md) - Incident response
- [Deployment Guide](../DEPLOYMENT_GUIDE.md) - Normal deployment process
- [Scaling Operations](scaling-operations.md) - Manual scaling procedures

## 📞 Escalation

If rollback fails or issues persist:
1. **Immediate**: Contact SRE Lead (PagerDuty)
2. **+15 min**: Escalate to Engineering Manager
3. **+30 min**: Engage GCP Support (P1 ticket)

---

**Last Updated**: February 2026  
**Maintained By**: SRE Team  
**Review Frequency**: Quarterly
