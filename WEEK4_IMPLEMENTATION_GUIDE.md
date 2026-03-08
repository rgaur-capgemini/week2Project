# Week 4 Implementation Guide - Enterprise RAG Chatbot

## Overview
Week 4 focuses on **production-ready observability, cost optimization, and experimentation**:

- **Vertex AI Experiments & Model Registry** for tracking variants
- **A/B Testing & Canary Releases** for safe rollouts
- **FinOps Dashboard** with budgets, alerts, and token tracking
- **End-to-end Observability** with SLO tracking and error budgets
- **Cost Optimization** achieving ≥15% reduction

---

## Table of Contents
1. [Architecture Changes](#architecture-changes)
2. [New Components](#new-components)
3. [Deployment Steps](#deployment-steps)
4. [FinOps Setup](#finops-setup)
5. [A/B Testing](#ab-testing)
6. [Observability](#observability)
7. [Cost Optimization](#cost-optimization)
8. [Verification](#verification)

---

## Architecture Changes

### New Services Added
```
app/experiments/          # A/B testing & experiments
├── experiment_tracker_week4.py
├── model_registry_week4.py
├── variant_manager_week4.py
├── ab_testing_week4.py
└── feature_flags_week4.py

app/finops/              # Cost tracking & budgets
├── cost_tracker_week4.py
├── budget_alerts_week4.py
└── token_usage_week4.py

app/observability/       # Monitoring & SLOs
├── metrics_collector_week4.py
├── synthetic_monitor_week4.py
└── error_budget_week4.py

app/experiment_routes_week4.py  # Experiments API
app/finops_routes_week4.py      # FinOps API
```

### Infrastructure Updates
```
k8s/
├── canary-deployment_week4.yaml    # Canary pods
└── monitoring-alerts_week4.yaml    # Alert configs

scripts/
├── apply_gcs_lifecycle_policies_week4.sh
├── setup_budgets_week4.sh
└── cost_optimization_analysis_week4.py
```

---

## New Components

### 1. Vertex AI Experiments
**Purpose**: Track prompt, model, and embedding variants

**Key Features**:
- Experiment runs with parameters & metrics
- Model registry for versioning
- Comparison tools for variant analysis

**Usage**:
```python
from app.experiments.experiment_tracker_week4 import ExperimentTracker

tracker = ExperimentTracker(PROJECT_ID, REGION)
run_id = tracker.log_prompt_variant(
    variant_name="concise_v1",
    prompt_template="You are a helpful assistant...",
    system_instruction="Be concise",
    temperature=0.3,
    metrics={"latency_ms": 245, "cost": 0.002}
)
```

### 2. A/B Testing Framework
**Purpose**: Test model/prompt variants with controlled traffic

**Key Features**:
- Consistent user assignment (sticky sessions)
- Traffic splitting (baseline vs variants)
- Gradual rollout with auto-rollback
- Success rate monitoring

**Usage**:
```python
from app.experiments.ab_testing_week4 import ABTestingFramework

# Select variant for user
variant_name, config = ab_testing.select_variant(user_id, VariantType.MODEL)

# Record interaction
ab_testing.record_interaction(variant_name, success=True, latency_ms=230)

# Gradual rollout
result = ab_testing.gradual_rollout(
    variant_name="gemini-flash-v1",
    target_percentage=50.0,
    increment=10.0
)
```

### 3. Feature Flags
**Purpose**: Control feature rollouts dynamically

**Predefined Flags**:
- `gemini_flash_model` - Use Flash instead of Pro (20% users)
- `cost_optimization` - Enable aggressive optimizations (100%)
- `detailed_observability` - Full trace logging (100%)

### 4. FinOps Dashboard
**Purpose**: Track costs, budgets, and token usage

**Components**:
- **Cost Tracker**: BigQuery billing export analysis
- **Budget Manager**: GCP Budget API integration
- **Token Tracker**: Real-time Vertex AI token monitoring

**API Endpoints**:
```
GET  /finops/costs/current-month       # Current costs
GET  /finops/costs/forecast            # Cost forecast
GET  /finops/tokens/vertex-ai          # Token usage
GET  /finops/dashboard                 # Unified dashboard
POST /finops/budgets                   # Create budget
```

### 5. Observability Stack
**Components**:
- **Metrics Collector**: Custom metrics to Cloud Monitoring
- **Synthetic Monitor**: Health check automation
- **Error Budget Tracker**: SLO compliance tracking

**SLOs Defined**:
- API Availability: 99.9%
- P95 Latency: < 500ms
- P99 Latency: < 1000ms

---

## Deployment Steps

### Step 1: Update main.py to include new routes

```python
# Add to app/main.py
from app.experiment_routes_week4 import router as experiment_router
from app.finops_routes_week4 import router as finops_router

app.include_router(experiment_router)
app.include_router(finops_router)
```

### Step 2: Install new dependencies

```bash
cd week3_btoproject_cloudrun_full

# Add to requirements.txt if not present:
# google-cloud-billing-budgets
# aiohttp

pip install -r requirements.txt
```

### Step 3: Configure Firestore collections

```bash
# Collections will be auto-created:
- experiment_variants
- feature_flags
- token_usage
- token_usage_daily
- error_budgets
- synthetic_checks
- application_metrics
```

### Step 4: Enable required APIs

```bash
gcloud services enable billingbudgets.googleapis.com --project=botpproject
gcloud services enable monitoring.googleapis.com --project=botpproject
```

### Step 5: Deploy canary deployment

```bash
# Deploy canary with 10% traffic
kubectl apply -f k8s/canary-deployment_week4.yaml

# Verify
kubectl get deployments
kubectl get pods -l version=canary
```

### Step 6: Configure monitoring alerts

```bash
kubectl apply -f k8s/monitoring-alerts_week4.yaml
```

---

## FinOps Setup

### 1. Export Billing Data to BigQuery

```bash
# In Cloud Console:
# Billing → Billing Export → Configure BigQuery Export
# Dataset: billing_export
# Table: gcp_billing_export_v1_XXXXXX
```

### 2. Create Budgets

**Option A: Using Script**
```bash
# Find billing account
gcloud beta billing accounts list

# Run setup script
bash scripts/setup_budgets_week4.sh botpproject BILLING_ACCOUNT_ID
```

**Option B: Manual via Console**
- Go to Billing → Budgets & alerts
- Create budget: "production-monthly-budget" ($2000)
- Thresholds: 50%, 75%, 90%, 100%

### 3. Apply GCS Lifecycle Policies

```bash
bash scripts/apply_gcs_lifecycle_policies_week4.sh botpproject
```

**Policies Applied**:
- NEARLINE after 30 days (65% cost reduction)
- COLDLINE after 90 days (80% cost reduction)
- ARCHIVE after 180 days (90% cost reduction)
- Delete temp/ and logs/ after 365 days

### 4. Run Cost Analysis

```bash
python3 scripts/cost_optimization_analysis_week4.py botpproject
```

**Expected Output**:
- Resource recommendations
- Potential monthly savings: $300-500
- Priority categorization

---

## A/B Testing

### Creating Variants

**1. Create Prompt Variant**
```bash
curl -X POST http://34.170.28.178.nip.io/experiments/variants \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "variant_name": "concise_prompt_v1",
    "variant_type": "prompt",
    "config": {
      "system_instruction": "Be concise and direct",
      "temperature": 0.3
    },
    "traffic_percentage": 20.0,
    "description": "Concise response variant"
  }'
```

**2. Create Model Variant (Gemini Flash)**
```bash
curl -X POST http://34.170.28.178.nip.io/experiments/variants \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "variant_name": "gemini_flash_v1",
    "variant_type": "model",
    "config": {
      "model_name": "gemini-1.5-flash-002",
      "temperature": 0.5
    },
    "traffic_percentage": 30.0,
    "description": "Cost-optimized Flash model"
  }'
```

**3. Activate Variant**
```bash
curl -X POST http://34.170.28.178.nip.io/experiments/variants/gemini_flash_v1/activate \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### Gradual Rollout

```bash
# Increase traffic gradually
curl -X POST http://34.170.28.178.nip.io/experiments/variants/gemini_flash_v1/rollout \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "target_percentage": 50.0,
    "increment": 10.0,
    "success_threshold": 95.0
  }'
```

### Monitoring Results

```bash
# Get experiment results
curl http://34.170.28.178.nip.io/experiments/results?variant_names=baseline,gemini_flash_v1 \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### Auto-Rollback

```bash
# Check if rollback needed (error rate > 5%)
curl -X POST http://34.170.28.178.nip.io/experiments/variants/gemini_flash_v1/check-rollback \
  -H "Authorization: Bearer $JWT_TOKEN"
```

---

## Observability

### 1. SLO Dashboard

```bash
# Get SLO metrics
curl http://34.170.28.178.nip.io/api/slo-metrics \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Response**:
```json
{
  "availability": {
    "target": 99.9,
    "actual": 99.95,
    "met": true
  },
  "latency": {
    "target_p95_ms": 500,
    "actual_p95_ms": 342,
    "met": true
  },
  "error_budget": {
    "remaining_percent": 87.5,
    "status": "healthy"
  }
}
```

### 2. Synthetic Monitoring

**Run Health Checks**:
```python
from app.observability.synthetic_monitor_week4 import SyntheticMonitor

monitor = SyntheticMonitor("http://34.170.28.178.nip.io", db)
results = await monitor.run_health_checks()
```

**Get Uptime Stats**:
```python
uptime_stats = monitor.get_uptime_stats(hours=24)
print(f"Uptime: {uptime_stats['uptime_percent']}%")
```

### 3. Error Budget Tracking

```python
from app.observability.error_budget_week4 import ErrorBudgetTracker

budget_tracker = ErrorBudgetTracker(db)

# Define error budget
budget_tracker.define_error_budget(
    service_name="rag-chatbot-api",
    slo_target=99.9,
    window_days=30
)

# Calculate status
status = budget_tracker.calculate_error_budget_status(
    service_name="rag-chatbot-api",
    total_requests=10000,
    failed_requests=5
)
```

---

## Cost Optimization

### Target: ≥15% Monthly Reduction

**Optimization Strategies**:

1. **Model Selection (40-50% of savings)**
   - Gemini Flash for simple queries: 70% cheaper
   - A/B test to maintain quality
   - Target: 50% Flash adoption = $200/month saved

2. **GCS Lifecycle Policies (20-30% of savings)**
   - Auto-transition to NEARLINE/COLDLINE
   - Delete temporary files
   - Target: $50-100/month saved

3. **GKE Autoscaling (10-15% of savings)**
   - Scale down during low traffic
   - Right-size node pools
   - Target: $50/month saved

4. **Embedding Caching (5-10% of savings)**
   - Cache in Redis/Firestore
   - Reduce duplicate embeddings
   - Target: $30-50/month saved

5. **Request Optimization (5-10% of savings)**
   - Batch embedding requests
   - Token limit controls
   - Target: $20-30/month saved

**Total Expected Savings**: $350-430/month (≥15% of $2000 baseline)

### Implementation Timeline

**Week 1**:
- ✓ Apply GCS lifecycle policies
- ✓ Enable GKE autoscaling
- ✓ Setup cost tracking & budgets

**Week 2**:
- Deploy Gemini Flash variant (10% traffic)
- Implement embedding caching
- Monitor cost impact

**Week 3**:
- Increase Flash traffic to 30-50%
- Optimize batch sizes
- Verify savings

**Week 4**:
- Full rollout if successful
- Document savings
- Continuous monitoring

---

## Verification

### 1. Check New Endpoints

```bash
# Experiments
curl http://34.170.28.178.nip.io/experiments/variants \
  -H "Authorization: Bearer $JWT_TOKEN"

# FinOps
curl http://34.170.28.178.nip.io/finops/costs/current-month \
  -H "Authorization: Bearer $JWT_TOKEN"

# FinOps Dashboard
curl http://34.170.28.178.nip.io/finops/dashboard \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### 2. Verify Canary Deployment

```bash
kubectl get deployments
# Should see: rag-backend, rag-backend-canary

kubectl get pods -l version=canary
# Should see: 1 canary pod running

kubectl logs -l version=canary --tail=50
# Check for CANARY_VARIANT=gemini-flash
```

### 3. Test A/B Selection

```bash
# User should consistently get same variant
for i in {1..5}; do
  curl http://34.170.28.178.nip.io/experiments/select-variant?variant_type=model \
    -H "Authorization: Bearer $JWT_TOKEN"
done
```

### 4. Check Error Budget

```bash
# View SLO compliance
curl http://34.170.28.178.nip.io/api/slo-metrics \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### 5. Verify Cost Tracking

```bash
# Check if token usage is being recorded
curl http://34.170.28.178.nip.io/finops/tokens/user-usage?days=7 \
  -H "Authorization: Bearer $JWT_TOKEN"
```

---

## Monitoring & Alerts

### Cloud Monitoring Dashboards

1. **FinOps Dashboard**
   - Current month costs by service
   - Token usage trends
   - Budget consumption
   - Cost anomalies

2. **SLO Dashboard**
   - Availability (99.9% target)
   - Latency (P95, P99)
   - Error budget remaining
   - Incident timeline

3. **Experiment Dashboard**
   - Active variants & traffic split
   - Variant performance metrics
   - A/B test results
   - Rollout progress

### Alert Policies

- Budget threshold alerts (50%, 75%, 90%, 100%)
- SLO violation alerts (availability < 99%)
- Error budget critical (< 20% remaining)
- Cost anomaly detection (> 50% increase)
- Canary rollback triggers (error rate > 5%)

---

## Troubleshooting

### Issue: Canary pods not getting traffic

**Solution**:
```bash
# Check ingress configuration
kubectl describe ingress rag-backend-canary-ingress

# Verify service selector
kubectl get svc rag-backend-canary -o yaml
```

### Issue: Cost data not appearing

**Solution**:
1. Verify billing export configured in BigQuery
2. Check dataset exists: `billing_export`
3. Grant BigQuery permissions to service account

### Issue: Experiments API returning errors

**Solution**:
```bash
# Check if Firestore collections created
# View pod logs
kubectl logs -l app=rag-backend --tail=100 | grep -i experiment
```

### Issue: Token usage not tracked

**Solution**:
- Ensure `record_token_usage` called after each Vertex AI request
- Check Firestore `token_usage_daily` collection
- Verify timestamps are recent

---

## Next Steps

1. **Monitor Cost Reduction** (30 days)
   - Track actual vs forecasted costs
   - Verify ≥15% reduction achieved
   - Adjust optimizations if needed

2. **Expand A/B Testing**
   - Test additional prompt variants
   - Compare embedding models
   - Measure quality vs cost tradeoffs

3. **Enhance Observability**
   - Add custom metrics
   - Create dashboards
   - Integrate with PagerDuty/Slack

4. **Production Hardening**
   - Implement rate limiting
   - Add request authentication
   - Setup disaster recovery

---

## Summary of Week 4 Deliverables

✅ **Vertex AI Experiments & Model Registry**
- Track variants and compare performance
- Version models in registry
- Automated experiment logging

✅ **A/B Testing & Canary Releases**
- Safe gradual rollouts
- Automatic rollback on errors
- Feature flags for control

✅ **FinOps Dashboard**
- Real-time cost tracking
- Budget alerts configured
- Token usage monitoring
- Cost forecasting

✅ **End-to-End Observability**
- SLO tracking (99.9% availability)
- Error budget monitoring
- Synthetic health checks
- Custom metrics collection

✅ **Cost Optimization**
- GCS lifecycle policies
- GKE autoscaling
- Model selection (Pro vs Flash)
- Target: ≥15% reduction

✅ **Production Readiness**
- Runbooks documented
- Alerts configured
- Monitoring dashboards
- 99.9% availability target

---

**Week 4 Status**: ✅ Complete

All files marked with `_week4` suffix for easy identification.

# _week4
