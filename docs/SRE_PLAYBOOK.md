# SRE Playbook - ChatBot RAG Application

## Service Level Objectives (SLOs)

### Availability SLO
- **Target**: 99.9% availability (43.8 minutes downtime/month)
- **Measurement Window**: 30 days rolling
- **Measurement Method**: Uptime checks on `/health` endpoint

### Latency SLO
- **Target**: 95% of requests complete in < 2000ms
- **Target**: 99% of requests complete in < 5000ms
- **Measurement**: End-to-end query latency

### Error Budget
- **Monthly Budget**: 0.1% error rate = ~43 minutes downtime
- **Policy**: Stop feature releases if budget exhausted

---

## Incident Response

### Severity Definitions

| Severity | Description | Response Time | Example |
|----------|-------------|---------------|---------|
| P0 | Complete outage | 15 minutes | All pods down |
| P1 | Major degradation | 30 minutes | >50% error rate |
| P2 | Minor degradation | 2 hours | High latency |
| P3 | Non-urgent issues | Next business day | UI glitch |

### Incident Response Workflow

```
1. DETECT → 2. ACKNOWLEDGE → 3. INVESTIGATE → 4. MITIGATE → 5. RESOLVE → 6. POSTMORTEM
```

### P0 Incident Checklist

- [ ] Acknowledge alert immediately
- [ ] Create incident channel (#incident-YYYY-MM-DD)
- [ ] Assign incident commander
- [ ] Check service status: `kubectl get pods --all-namespaces`
- [ ] Check recent deployments: `kubectl rollout history deployment/chatbot-rag-backend`
- [ ] Review error logs: `kubectl logs -l app=chatbot-rag --tail=200`
- [ ] Engage on-call engineer if needed
- [ ] Communicate status to stakeholders every 30 minutes
- [ ] Document all actions taken

---

## Common Incidents and Resolutions

### 1. Complete Service Outage

**Symptoms:**
- Health check failing
- All pods in CrashLoopBackOff
- Ingress returning 503

**Investigation:**
```bash
# Check pod status
kubectl get pods -o wide

# Check events
kubectl get events --sort-by='.lastTimestamp' | tail -20

# Check recent deployments
kubectl rollout history deployment/chatbot-rag-backend
```

**Resolution:**
```bash
# Option 1: Rollback to previous version
kubectl rollout undo deployment/chatbot-rag-backend

# Option 2: Scale to zero and back (force restart)
kubectl scale deployment chatbot-rag-backend --replicas=0
kubectl scale deployment chatbot-rag-backend --replicas=3

# Option 3: Delete and recreate pods
kubectl delete pods -l app=chatbot-rag,component=backend
```

**Prevention:**
- Implement proper readiness/liveness probes
- Use Blue/Green deployments
- Enforce deployment gates in CI/CD

---

### 2. High Error Rate (>5%)

**Symptoms:**
- Increased 500 errors
- Error rate alerts firing
- User complaints

**Investigation:**
```bash
# Check error logs
kubectl logs -l component=backend --tail=500 | grep ERROR

# Check Cloud Logging
gcloud logging read "severity=ERROR AND resource.type=k8s_container" \
  --limit=100 --format=json

# Check application metrics
# Navigate to Cloud Console > Monitoring > Metrics Explorer
```

**Common Causes:**
1. **Vertex AI Rate Limiting**
   - Check quota usage
   - Implement exponential backoff
   - Request quota increase

2. **Redis Connection Failures**
   ```bash
   # Verify Redis instance
   gcloud redis instances describe chatbot-chat-history --region=us-central1
   
   # Test connectivity
   kubectl exec -it <pod> -- nc -zv <REDIS_HOST> 6379
   ```

3. **Database Timeout**
   - Check Firestore metrics
   - Review query complexity
   - Add indexes if needed

**Resolution:**
- Implement circuit breakers
- Add retry logic with backoff
- Scale up resources if capacity issue

---

### 3. High Latency (P95 > 5s)

**Symptoms:**
- Slow response times
- Timeout errors
- Poor user experience

**Investigation:**
```bash
# Check Cloud Trace
gcloud trace list --limit=20

# Check pod resource usage
kubectl top pods

# Check HPA status
kubectl get hpa

# Review analytics dashboard for latency breakdown
```

**Common Causes:**
1. **Vector Search Performance**
   - Check index size and sharding
   - Tune `top_k` parameter
   - Enable caching for frequent queries

2. **LLM Generation Slowness**
   - Check Vertex AI endpoint health
   - Consider using faster model variant
   - Implement streaming responses

3. **Database Query Slowness**
   - Add Firestore composite indexes
   - Optimize query patterns
   - Enable caching layer

**Resolution:**
```bash
# Scale up pods
kubectl scale deployment chatbot-rag-backend --replicas=6

# Increase resource limits
kubectl set resources deployment chatbot-rag-backend \
  --limits=cpu=2,memory=4Gi \
  --requests=cpu=1,memory=2Gi
```

---

### 4. Out of Memory (OOM)

**Symptoms:**
- Pods restarting frequently
- OOMKilled events
- Application crashes

**Investigation:**
```bash
# Check pod events
kubectl describe pod <pod-name> | grep -A 5 "Last State"

# Check resource usage
kubectl top pods

# Check memory limits
kubectl describe pod <pod-name> | grep -A 5 "Limits"
```

**Resolution:**
```bash
# Immediate: Increase memory limits
kubectl set resources deployment chatbot-rag-backend \
  --limits=memory=4Gi \
  --requests=memory=2Gi

# Longer-term: Investigate memory leaks
# - Profile application
# - Check for unclosed connections
# - Review caching strategies
```

---

### 5. Redis Connection Issues

**Symptoms:**
- Chat history not saving
- Session errors
- Redis connection timeout logs

**Investigation:**
```bash
# Check Redis instance status
gcloud redis instances describe chatbot-chat-history \
  --region=us-central1

# Check network connectivity
kubectl run redis-test --rm -it --image=redis:latest -- \
  redis-cli -h <REDIS_HOST> ping

# Check application logs
kubectl logs -l component=backend | grep -i redis
```

**Resolution:**
```bash
# 1. Verify Redis instance is running
gcloud redis instances list --region=us-central1

# 2. Check authorized networks
gcloud redis instances describe chatbot-chat-history \
  --region=us-central1 | grep authorizedNetwork

# 3. Restart Redis connections
kubectl rollout restart deployment/chatbot-rag-backend

# 4. If persistent, recreate Redis instance
terraform taint google_redis_instance.chat_history
terraform apply
```

---

### 6. Authentication Failures

**Symptoms:**
- Users unable to login
- 401 Unauthorized errors
- Token validation failures

**Investigation:**
```bash
# Check auth service logs
kubectl logs -l component=backend | grep -i "auth\|token\|401"

# Verify Google OIDC configuration
echo $GOOGLE_CLIENT_IDS

# Check secret availability
kubectl get secret app-secrets
kubectl describe secret app-secrets
```

**Resolution:**
```bash
# 1. Verify client IDs are correct
kubectl create secret generic app-secrets \
  --from-literal=google_client_ids="CORRECT_CLIENT_ID" \
  --dry-run=client -o yaml | kubectl apply -f -

# 2. Restart backend to pick up changes
kubectl rollout restart deployment/chatbot-rag-backend

# 3. Clear user token cache if needed
# Users need to logout and login again
```

---

### 7. Deployment Failures

**Symptoms:**
- Deployment stuck in progress
- Pods not reaching ready state
- CI/CD pipeline failures

**Investigation:**
```bash
# Check rollout status
kubectl rollout status deployment/chatbot-rag-backend

# Check pod status
kubectl get pods -l component=backend

# Check image pull status
kubectl describe pod <pod-name> | grep -A 10 "Events"
```

**Resolution:**
```bash
# Option 1: Wait for rollout (if progressing)
kubectl rollout status deployment/chatbot-rag-backend --timeout=10m

# Option 2: Rollback if failing
kubectl rollout undo deployment/chatbot-rag-backend

# Option 3: Check image exists
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/btoproject-486405/chatbot-rag-images/backend

# Option 4: Fix and redeploy
# Fix issue, rebuild image, redeploy
```

---

## Monitoring and Alerting

### Critical Alerts

1. **Service Down**
   - Trigger: All pods unhealthy for 5 minutes
   - Action: P0 incident, immediate response

2. **High Error Rate**
   - Trigger: >5% error rate for 10 minutes
   - Action: P1 incident, investigate within 30 minutes

3. **High Latency**
   - Trigger: P95 latency >5s for 10 minutes
   - Action: P2 incident, investigate within 2 hours

4. **Resource Exhaustion**
   - Trigger: CPU >90% or Memory >90% for 10 minutes
   - Action: P2 incident, scale resources

### Alert Configuration

```yaml
# Example alert policy (Cloud Monitoring)
displayName: "High Error Rate Alert"
conditions:
  - displayName: "Error rate > 5%"
    conditionThreshold:
      filter: 'metric.type="loadbalancing.googleapis.com/https/request_count"'
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_RATE
      comparison: COMPARISON_GT
      thresholdValue: 0.05
      duration: 600s
notificationChannels:
  - "projects/btoproject-486405/notificationChannels/CHANNEL_ID"
```

---

## Capacity Planning

### Growth Projections

| Metric | Current | 3 Months | 6 Months |
|--------|---------|----------|----------|
| Daily Active Users | 100 | 500 | 1000 |
| Queries/Day | 1000 | 5000 | 10000 |
| Documents | 1000 | 5000 | 10000 |
| Storage (GB) | 10 | 50 | 100 |

### Scaling Triggers

- **Scale Up**: When CPU >70% or Memory >80% sustained for 10 minutes
- **Scale Down**: When CPU <30% and Memory <40% for 30 minutes
- **Node Addition**: When cluster CPU >80% overall

### Resource Recommendations

```yaml
# Current configuration
Backend:
  replicas: 3-10
  cpu: 500m-1000m
  memory: 1Gi-2Gi

Frontend:
  replicas: 2-6
  cpu: 200m-500m
  memory: 256Mi-512Mi

Nodes:
  type: e2-standard-4
  min: 2
  max: 10
```

---

## Maintenance Windows

### Scheduled Maintenance
- **Day**: Sunday 02:00-04:00 UTC
- **Frequency**: Monthly
- **Activities**: Updates, patches, configuration changes

### Maintenance Procedure

```bash
# 1. Notify stakeholders 48 hours in advance

# 2. Take backup
gcloud firestore export gs://btoproject-486405-backups/$(date +%Y%m%d)

# 3. Perform maintenance
# - Update configurations
# - Apply patches
# - Upgrade dependencies

# 4. Test in staging

# 5. Deploy to production
kubectl apply -f infra/kubernetes/deployment.yaml

# 6. Monitor for 30 minutes post-deployment

# 7. Send completion notification
```

---

## Disaster Recovery

### RTO and RPO
- **RTO (Recovery Time Objective)**: 1 hour
- **RPO (Recovery Point Objective)**: 1 hour

### DR Procedure

```bash
# 1. Declare disaster
# 2. Assess impact and data loss
# 3. Initialize recovery cluster (if needed)

terraform apply -target=google_container_cluster.primary

# 4. Restore data
gcloud firestore import gs://btoproject-486405-backups/LATEST

# 5. Deploy application
kubectl apply -f infra/kubernetes/deployment.yaml

# 6. Validate functionality
./scripts/smoke_tests.py

# 7. Switch traffic (update DNS if needed)
# 8. Monitor closely for 4 hours
# 9. Conduct post-recovery review
```

---

## Postmortem Template

```markdown
# Incident Postmortem - [Date] - [Brief Title]

## Incident Summary
- **Date**: 
- **Duration**: 
- **Severity**: 
- **Impact**: 

## Timeline
- HH:MM - Event 1
- HH:MM - Event 2

## Root Cause

## Resolution

## Action Items
- [ ] Item 1 - Owner: - Due:
- [ ] Item 2 - Owner: - Due:

## Lessons Learned

## What Went Well

## What Could Be Improved
```

---

*Last Updated: February 2026*
*Maintained by: SRE Team*
*Review Cycle: Quarterly*
