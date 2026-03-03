# Week 4 Deployment Guide

## Prerequisites

✅ Week 1-3 features deployed and operational  
✅ GKE cluster running with backend and frontend  
✅ Vertex AI API enabled  
✅ Cloud Monitoring configured  
✅ kubectl configured to access cluster  

---

## Step 1: Update Backend Code

### 1.1 Pull Latest Code

```bash
cd week3_btoproject_cloudrun_full
git pull origin main  # or your branch
```

### 1.2 Build New Backend Image

```bash
# Build with Week 4 features
docker build -t gcr.io/btoproject-486405/rag-backend:week4 .

# Push to GCR
docker push gcr.io/btoproject-486405/rag-backend:week4
```

### 1.3 Update Backend Deployment

```bash
# Update image
kubectl set image deployment/rag-backend \
  backend=gcr.io/btoproject-486405/rag-backend:week4

# Wait for rollout
kubectl rollout status deployment/rag-backend

# Verify pods are running
kubectl get pods -l app=rag-backend
```

---

## Step 2: Apply Cost Optimizations

### 2.1 Update HPA Configuration

```bash
# Apply optimized HPA
kubectl apply -f k8s/hpa.yaml

# Verify HPA
kubectl get hpa
```

Expected output:
```
NAME                 REFERENCE               TARGETS    MINPODS   MAXPODS
rag-backend-hpa      Deployment/rag-backend  50%/70%    2         20
rag-frontend-hpa     Deployment/rag-frontend 30%/70%    1         10
```

### 2.2 Apply GCS Lifecycle Policies

```bash
# Set environment variable
export PROJECT_ID=btoproject-486405

# Apply policies
bash scripts/apply_gcs_lifecycle_policies.sh
```

---

## Step 3: Deploy Monitoring Infrastructure

### 3.1 Create Observability Dashboard

```bash
bash scripts/create_observability_dashboard.sh

# Apply the dashboard
gcloud monitoring dashboards create --config-from-file=observability-dashboard.json
```

### 3.2 Create Log-Based Metrics

```bash
bash scripts/create_log_metrics.sh
```

### 3.3 Set Up Alert Policies

```bash
# Create alert YAML files
bash scripts/create_alert_policies.sh

# Apply alerts (requires notification channel)
# 1. Create notification channel in Cloud Console
# 2. Get channel ID
# 3. Apply policies with channel ID
```

### 3.4 Set Up Synthetic Monitoring

```bash
bash scripts/setup_synthetic_monitoring.sh
```

---

## Step 4: Deploy Canary Infrastructure

### 4.1 Build Canary Image (Optional)

```bash
# For testing, use same image as stable
docker tag gcr.io/btoproject-486405/rag-backend:week4 \
           gcr.io/btoproject-486405/rag-backend:canary

docker push gcr.io/btoproject-486405/rag-backend:canary
```

### 4.2 Deploy Canary Deployment

```bash
# Deploy canary resources
kubectl apply -f k8s/canary-deployment.yaml

# Verify canary pod is running
kubectl get pods -l version=canary
```

### 4.3 Test Canary Monitoring (Optional)

```bash
# Run monitor for 5 minutes
python scripts/canary_monitor.py --interval 60 --iterations 5
```

---

## Step 5: Update Frontend

### 5.1 Build Frontend with FinOps Component

```bash
cd frontend

# Install dependencies (if not already done)
npm install

# Build production
ng build --configuration=production
```

### 5.2 Build and Deploy Frontend Image

```bash
# Build image
docker build -t gcr.io/btoproject-486405/rag-frontend:week4 .

# Push to GCR
docker push gcr.io/btoproject-486405/rag-frontend:week4

# Update deployment
kubectl set image deployment/rag-frontend \
  frontend=gcr.io/btoproject-486405/rag-frontend:week4

# Wait for rollout
kubectl rollout status deployment/rag-frontend
```

---

## Step 6: Verification

### 6.1 Test New API Endpoints

```bash
# Get backend URL
BACKEND_URL=$(kubectl get service rag-backend-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Get admin JWT token (login via frontend first)
export TOKEN="your-jwt-token"

# Test FinOps endpoint
curl -H "Authorization: Bearer $TOKEN" \
  http://$BACKEND_URL/finops/dashboard

# Test experiments endpoint
curl -H "Authorization: Bearer $TOKEN" \
  http://$BACKEND_URL/experiments/list
```

### 6.2 Access FinOps Dashboard

1. Navigate to frontend: `http://<FRONTEND_IP>`
2. Login as admin
3. Navigate to FinOps dashboard
4. Verify cost data is displayed

### 6.3 Run Cost Analysis

```bash
# Get cost optimization recommendations
python scripts/cost_optimization_analysis.py
```

### 6.4 Run SLO Tracker

```bash
# Check SLO compliance
python scripts/slo_tracker.py --period-days 30
```

### 6.5 Test Synthetic Monitoring

```bash
# Run manual synthetic test
export BACKEND_URL=http://$BACKEND_URL
bash scripts/synthetic_monitoring.sh
```

---

## Step 7: Configure Monitoring & Alerts

### 7.1 Create Notification Channels

```bash
# Email notification
gcloud alpha monitoring channels create \
  --display-name="SRE Team Email" \
  --type=email \
  --channel-labels=email_address=sre-team@company.com

# Get channel ID
gcloud alpha monitoring channels list
```

### 7.2 Update Alert Policies

Update `scripts/create_alert_policies.sh` with your notification channel ID, then:

```bash
# Apply alerts
bash scripts/create_alert_policies.sh
```

---

## Step 8: Post-Deployment Validation

### 8.1 Check All Pods

```bash
kubectl get pods --all-namespaces

# Should see:
# - 2+ rag-backend pods
# - 1+ rag-frontend pods
# - 0-1 rag-backend-canary pods
```

### 8.2 Check HPA Status

```bash
kubectl get hpa

# Should show current metrics
```

### 8.3 Check Monitoring

```bash
# View dashboards
https://console.cloud.google.com/monitoring/dashboards?project=btoproject-486405

# Check uptime checks
gcloud monitoring uptime-checks list
```

### 8.4 Check Cost Optimization

```bash
# Run analysis
python scripts/cost_optimization_analysis.py

# Should show 15%+ projected savings
```

---

## Rollback Procedure

If issues arise, rollback to Week 3:

```bash
# Rollback backend
kubectl set image deployment/rag-backend \
  backend=gcr.io/btoproject-486405/rag-backend:week3

# Rollback frontend
kubectl set image deployment/rag-frontend \
  frontend=gcr.io/btoproject-486405/rag-frontend:week3

# Remove canary
kubectl delete -f k8s/canary-deployment.yaml

# Verify
kubectl get pods
```

---

## Troubleshooting

### Backend Pods CrashLooping

```bash
# Check logs
kubectl logs -l app=rag-backend --tail=100

# Common issues:
# - Missing dependencies → Check requirements.txt
# - Config errors → Verify ConfigMap
# - Import errors → Check new module imports
```

### FinOps Dashboard Empty

```bash
# Check backend logs
kubectl logs -l app=rag-backend | grep finops

# Verify admin role
# Access /auth/user endpoint and check role

# Mock data is used by default
# To use real data, configure BigQuery billing export
```

### Experiments Not Working

```bash
# Check Vertex AI API enabled
gcloud services list --enabled | grep aiplatform

# Check service account permissions
gcloud projects get-iam-policy btoproject-486405 \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:rag-backend-sa@*"

# Grant permissions if needed
gcloud projects add-iam-policy-binding btoproject-486405 \
  --member="serviceAccount:rag-backend-sa@btoproject-486405.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

### Canary Monitor Fails

```bash
# Install dependencies
pip install google-cloud-monitoring

# Check project ID
echo $PROJECT_ID

# Test with verbose output
python scripts/canary_monitor.py --help
```

---

## Success Criteria

✅ Backend pods running with week4 image  
✅ Frontend pods running with week4 image  
✅ FinOps dashboard accessible and showing data  
✅ Experiment endpoints responding  
✅ Cost optimization showing ≥15% savings  
✅ SLO tracker running without errors  
✅ Synthetic monitoring passing  
✅ Observability dashboard created  
✅ HPA configured with optimized settings  
✅ GCS lifecycle policies applied  

---

## Next Steps

1. **Monitor for 24 hours**: Watch for any issues
2. **Run first experiment**: Compare Flash vs Pro models
3. **Deploy canary**: Test new features with canary process
4. **Review costs**: Check FinOps dashboard daily
5. **Optimize further**: Use recommendations from cost analysis

---

## Support

- **Documentation**: [WEEK4_IMPLEMENTATION.md](../WEEK4_IMPLEMENTATION.md)
- **SRE Procedures**: [WEEK4_SRE_PROCEDURES.md](WEEK4_SRE_PROCEDURES.md)
- **Logs**: `kubectl logs -f deployment/rag-backend`
- **Metrics**: Cloud Console Monitoring

---

**Deployment Guide Version**: 1.0  
**Last Updated**: 2026-02-28
