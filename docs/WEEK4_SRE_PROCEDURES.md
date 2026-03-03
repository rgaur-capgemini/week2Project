# Week 4 SRE Procedures - Advanced Operations

## Overview

Week 4 adds enterprise-grade operational capabilities:
- SLO tracking with error budgets
- Canary deployments with automated monitoring
- FinOps dashboard and cost management
- Experiment tracking and A/B testing
- Enhanced observability and synthetic monitoring

---

## SLO Management & Error Budgets

### Monthly SLO Review

Run SLO tracker to check compliance:
```bash
python scripts/slo_tracker.py --period-days 30
```

**Error Budget Actions**:
- **> 50% remaining**: Safe to deploy, experiment freely
- **20-50% remaining**: Proceed with caution, limit deployments
- **< 20% remaining**: Feature freeze, focus on reliability
- **0% remaining**: Emergency mode - fix issues, no new features

**Error Budget Burn Rate Alerts**:
- Fast burn: >2% in 1 hour → Immediate investigation
- Slow burn: >10% in 6 hours → Scheduled investigation

---

## Canary Deployment Process

### Deploy Canary

```bash
# 1. Build and push canary image
docker build -t gcr.io/btoproject-486405/rag-backend:canary .
docker push gcr.io/btoproject-486405/rag-backend:canary

# 2. Deploy canary (starts with 10% traffic)
kubectl apply -f k8s/canary-deployment.yaml

# 3. Verify canary pods are running
kubectl get pods -l version=canary
```

### Monitor Canary

```bash
# Automated monitoring (runs for 60 minutes)
python scripts/canary_monitor.py --interval 60 --iterations 60

# Manual health check
kubectl logs -l version=canary --tail=100
```

### Canary Decision Tree

1. **Monitor for 15 minutes**
   - Error rate < 5% AND
   - Latency p95 < 2s AND
   - No crashes
   → Proceed to 25% traffic

2. **Monitor for 30 minutes total**
   - Metrics remain healthy
   → Proceed to 50% traffic

3. **Monitor for 45 minutes total**
   - Metrics remain healthy
   → Proceed to 100% (promotion)

### Promote Canary

```bash
# Update stable deployment
kubectl set image deployment/rag-backend \
  backend=gcr.io/btoproject-486405/rag-backend:canary

# Scale down canary
kubectl scale deployment rag-backend-canary --replicas=0
```

### Rollback Canary

```bash
# Immediate rollback
kubectl scale deployment rag-backend-canary --replicas=0

# Verify traffic back to stable
kubectl get pods -l app=rag-backend
```

---

## FinOps Cost Management

### Daily Cost Monitoring

```bash
# Check FinOps dashboard
# Access: http://frontend-url/finops (admin only)
```

### Weekly Cost Review

```bash
# Run cost optimization analysis
python scripts/cost_optimization_analysis.py

# Check for anomalies
curl -H "Authorization: Bearer $TOKEN" \
  http://rag-backend-service/finops/anomalies
```

### Cost Anomaly Response

1. **Spike > 20% from baseline**:
   - Check service logs for unusual activity
   - Review token usage: `GET /finops/token-usage`
   - Verify no runaway processes

2. **Vertex AI cost spike**:
   ```bash
   # Check token usage by model
   GET /finops/token-usage?days=7
   
   # Review recent experiments
   GET /experiments/list
   ```

3. **GKE cost spike**:
   ```bash
   # Check pod count
   kubectl get pods --all-namespaces | wc -l
   
   # Check HPA status
   kubectl get hpa
   ```

### Budget Alert Response

- **75% threshold**: Review optimization opportunities
- **90% threshold**: Implement immediate cost controls
- **100% threshold**: Emergency cost reduction measures

---

## Experiment Management

### Run Model Comparison

```bash
# Via API
POST /experiments/run
{
  "experiment_type": "model",
  "variants": {
    "models": ["gemini-2.0-flash-001", "gemini-1.5-pro"]
  },
  "test_cases": [...]
}
```

### View Experiment Results

```bash
# List experiments
GET /experiments/list

# Get specific experiment
GET /experiments/{experiment_id}

# View in Vertex AI Console
https://console.cloud.google.com/vertex-ai/experiments
```

### Experiment Rollout Decision

1. Compare metrics (latency, tokens, cost)
2. If new variant shows >10% improvement → Deploy as canary
3. Monitor canary performance
4. Promote if healthy

---

## Synthetic Monitoring

### Setup (one-time)

```bash
bash scripts/setup_synthetic_monitoring.sh
```

### Manual Test

```bash
bash scripts/synthetic_monitoring.sh
```

### Synthetic Test Failure Response

1. **Health check fails**:
   ```bash
   # Check pod health
   kubectl get pods -l app=rag-backend
   
   # Check recent deployments
   kubectl rollout history deployment/rag-backend
   ```

2. **Query endpoint fails**:
   ```bash
   # Check backend logs
   kubectl logs -l app=rag-backend --tail=200 | grep "query"
   
   # Check Vertex AI quota
   gcloud ai quotas list --region=us-central1
   ```

3. **High latency detected**:
   ```bash
   # Check pod resources
   kubectl top pods -l app=rag-backend
   
   # Check HPA status
   kubectl get hpa rag-backend-hpa
   ```

---

## Observability Dashboard

### Access Dashboard

```bash
# Cloud Console
https://console.cloud.google.com/monitoring/dashboards?project=btoproject-486405
```

### Key Metrics to Monitor

1. **Request Rate**: Should be consistent, spikes indicate issues
2. **Error Rate**: Target < 1%
3. **Latency p95**: Target < 2s
4. **Pod CPU/Memory**: Should be < 80% on average
5. **SLO Compliance**: Should be green

### Dashboard Alerts

- Red tile: Immediate action required
- Yellow tile: Investigation needed
- Green tile: Healthy

---

## Cost Optimization Procedures

### Apply GCS Lifecycle Policies

```bash
bash scripts/apply_gcs_lifecycle_policies.sh
```

### Resource Right-Sizing

```bash
# Get recommendations
python scripts/cost_optimization_analysis.py

# Review output for:
# - Pod CPU/memory recommendations
# - Storage lifecycle opportunities
# - Node pool optimizations
```

### Implement Recommendations

1. Update deployment resource requests
2. Adjust HPA settings
3. Configure storage lifecycle
4. Enable committed use discounts (for long-term)

---

## Log-Based Metrics

### View Custom Metrics

```bash
# List all log-based metrics
gcloud logging metrics list --project=btoproject-486405

# View specific metric
gcloud logging metrics describe compliance_workflow_failures
```

### Alert on Custom Metrics

- Compliance workflow failures → Investigate agent issues
- Vertex AI errors → Check quotas and permissions
- Auth failures → Security review
- High latency requests → Performance investigation

---

## Week 4 Monitoring Checklist

### Daily
- [ ] Check FinOps dashboard for cost anomalies
- [ ] Review error budget consumption
- [ ] Verify synthetic monitoring passing

### Weekly
- [ ] Run cost optimization analysis
- [ ] Review SLO compliance
- [ ] Check canary deployment health (if active)
- [ ] Review experiment results

### Monthly
- [ ] Generate SLO report
- [ ] Review and adjust budgets
- [ ] Update cost optimization recommendations
- [ ] Capacity planning review

---

## Troubleshooting: Week 4 Features

### Canary Issues

**Canary pods not starting**:
```bash
# Check pod status
kubectl describe pod -l version=canary

# Check image availability
docker pull gcr.io/btoproject-486405/rag-backend:canary
```

**Canary monitor script fails**:
```bash
# Check Python dependencies
pip install google-cloud-monitoring

# Verify project ID
echo $PROJECT_ID

# Run with verbose logging
python scripts/canary_monitor.py --help
```

### FinOps Issues

**Dashboard shows no data**:
```bash
# Check backend logs
kubectl logs -l app=rag-backend | grep finops

# Test endpoint directly
curl -H "Authorization: Bearer $TOKEN" \
  http://rag-backend-service/finops/dashboard

# Verify admin role
GET /auth/user (check user.role == "admin")
```

**Cost data inaccurate**:
- Enable BigQuery billing export
- Grant billing.viewer role to service account
- Replace mock data with actual queries

### Experiment Tracking Issues

**Experiments not visible in Vertex AI**:
```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com

# Grant permissions
gcloud projects add-iam-policy-binding btoproject-486405 \
  --member="serviceAccount:rag-backend-sa@..." \
  --role="roles/aiplatform.user"
```

**Experiment run fails**:
```bash
# Check logs
kubectl logs -l app=rag-backend | grep experiment

# Verify region
echo $VERTEX_LOCATION  # Should be us-central1
```

---

**Week 4 Procedures Version**: 1.0  
**Last Updated**: 2026-02-28  
**Owner**: SRE Team
