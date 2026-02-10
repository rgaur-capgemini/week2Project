# Scaling Operations Runbook

## 📋 Purpose

Procedures for scaling the RAG Chatbot system - both manual scaling for planned events and managing auto-scaling configurations.

## 📊 Current Scaling Configuration

### Auto-Scaling Limits (HPA)

#### Backend
- **Min replicas**: 3
- **Max replicas**: 20
- **Target CPU**: 70%
- **Target Memory**: 80%
- **Scale-up stabilization**: 60 seconds
- **Scale-down stabilization**: 300 seconds

#### Frontend
- **Min replicas**: 2
- **Max replicas**: 10
- **Target CPU**: 70%
- **Target Memory**: 80%

### Node Pool Auto-Scaling
- **Min nodes**: 1
- **Max nodes**: 10
- **Machine type**: n1-standard-2 (2 vCPU, 7.5GB RAM)

---

## 🔑 Prerequisites

### Required Access
- GKE Admin (`roles/container.admin`)
- Kubernetes RBAC: cluster-admin or edit permissions

### Required Tools
```bash
kubectl version --client  # >= 1.28
gcloud version            # Latest
```

---

## 📈 Manual Scaling Procedures

### 1. Pre-Event Scaling (Planned Traffic Increase)

Use this for:
- Marketing campaigns
- Product launches
- Known traffic spikes
- Maintenance windows

#### 1.1 Assess Expected Load

```bash
# Check current metrics
kubectl top pods -l app=rag-backend
kubectl top nodes

# Check current replica count
kubectl get hpa

# Check recent traffic patterns
gcloud logging read "resource.type=k8s_container \
  resource.labels.namespace_name=default" \
  --limit 1000 \
  --format json | jq '.[] | .httpRequest.requestUrl' | sort | uniq -c
```

**Calculate target replicas**:
- Current RPS (Requests Per Second): e.g., 100
- Expected RPS: e.g., 500 (5x increase)
- Current replicas: 3
- Target replicas: 3 × 5 = **15 replicas**

---

#### 1.2 Scale Backend Deployment

```bash
# Scale backend to handle expected load
kubectl scale deployment rag-backend --replicas=15

# Monitor scaling progress
kubectl get pods -l app=rag-backend -w

# Wait for all pods to be ready
kubectl wait --for=condition=ready pod -l app=rag-backend --timeout=300s
```

**Duration**: 3-5 minutes for pods to start and become ready

---

#### 1.3 Scale Frontend Deployment

```bash
# Scale frontend proportionally
kubectl scale deployment rag-frontend --replicas=8

# Monitor
kubectl get pods -l app=rag-frontend -w

# Wait for ready
kubectl wait --for=condition=ready pod -l app=rag-frontend --timeout=300s
```

---

#### 1.4 Pre-warm GKE Node Pool

```bash
# Check current node count
kubectl get nodes

# If needed, manually scale node pool
gcloud container clusters resize rag-chatbot-cluster \
  --num-nodes 8 \
  --region us-central1

# Monitor node addition
watch kubectl get nodes
```

**Duration**: 3-5 minutes per node

---

#### 1.5 Verify Scaling

```bash
# Check deployment status
kubectl get deployments

# Check pod distribution across nodes
kubectl get pods -l app=rag-backend -o wide

# Check resource utilization
kubectl top pods -l app=rag-backend
kubectl top nodes

# Test endpoints
SERVICE_URL=$(kubectl get service rag-backend-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl http://${SERVICE_URL}/health
```

---

#### 1.6 Load Test (Recommended)

```bash
# Install hey (HTTP load generator)
go install github.com/rakyll/hey@latest

# Load test backend
hey -n 10000 -c 100 -m POST \
  -H "Content-Type: application/json" \
  -d '{"question":"test query","top_k":3}' \
  http://${SERVICE_URL}/query

# Monitor during load test
kubectl top pods -l app=rag-backend
kubectl get hpa -w
```

---

### 2. Emergency Scaling (During Incident)

Use this for:
- Unexpected traffic spike
- DDoS attack
- Service degradation

#### 2.1 Quick Scale-Up

```bash
# Immediate scale to max capacity
kubectl scale deployment rag-backend --replicas=20
kubectl scale deployment rag-frontend --replicas=10

# Increase node pool if needed
gcloud container clusters resize rag-chatbot-cluster \
  --num-nodes 10 \
  --region us-central1

# Monitor
watch kubectl get pods
```

---

#### 2.2 Enable Rate Limiting (If Not Already)

```bash
# Check current rate limit config
kubectl get configmap rag-config -o yaml | grep RATE_LIMIT

# Update rate limit (if needed)
kubectl patch configmap rag-config \
  -p '{"data":{"RATE_LIMIT_PER_MINUTE":"30"}}'

# Restart to apply new config
kubectl rollout restart deployment/rag-backend
```

---

#### 2.3 Monitor Impact

```bash
# Watch pod metrics
kubectl top pods -l app=rag-backend --watch

# Check error rate
kubectl logs -l app=rag-backend --tail=100 | grep ERROR | wc -l

# Check Cloud Monitoring
# Navigate to: https://console.cloud.google.com/monitoring
# Dashboard: RAG Backend Performance
```

---

### 3. Post-Event Scale-Down

#### 3.1 Monitor Traffic Return to Normal

```bash
# Check current request rate
kubectl logs -l app=rag-backend --tail=1000 | grep "POST /query" | wc -l

# Check resource utilization
kubectl top pods -l app=rag-backend

# If CPU < 30% and memory < 50% for > 15 minutes, safe to scale down
```

---

#### 3.2 Gradual Scale-Down

```bash
# Scale down gradually (not all at once)
# From 15 replicas → 10 replicas
kubectl scale deployment rag-backend --replicas=10

# Wait 10 minutes, monitor
watch kubectl top pods -l app=rag-backend

# If stable, continue scaling down
# From 10 → 5
kubectl scale deployment rag-backend --replicas=5

# Wait 10 minutes
# From 5 → 3 (baseline)
kubectl scale deployment rag-backend --replicas=3
```

**Best Practice**: Scale down in steps, monitoring between each step.

---

#### 3.3 Scale Down Frontend

```bash
# Scale frontend back to baseline
kubectl scale deployment rag-frontend --replicas=2

# Verify
kubectl get deployments
```

---

#### 3.4 Scale Down Node Pool (Optional)

```bash
# Let GKE auto-scaler handle this naturally
# Or manually scale down after 30-60 minutes

gcloud container clusters resize rag-chatbot-cluster \
  --num-nodes 3 \
  --region us-central1
```

---

## ⚙️ HPA Configuration Management

### 1. View Current HPA Configuration

```bash
# List all HPAs
kubectl get hpa

# Describe HPA for backend
kubectl describe hpa rag-backend-hpa

# Get HPA YAML
kubectl get hpa rag-backend-hpa -o yaml
```

---

### 2. Update HPA Thresholds

#### 2.1 Update CPU Target

```bash
# Update target CPU utilization from 70% to 60%
kubectl patch hpa rag-backend-hpa \
  -p '{"spec":{"metrics":[{"type":"Resource","resource":{"name":"cpu","target":{"type":"Utilization","averageUtilization":60}}}]}}'

# Verify
kubectl get hpa rag-backend-hpa -o yaml
```

---

#### 2.2 Update Min/Max Replicas

```bash
# Update min replicas from 3 to 5 (higher baseline)
kubectl patch hpa rag-backend-hpa \
  -p '{"spec":{"minReplicas":5}}'

# Update max replicas from 20 to 30
kubectl patch hpa rag-backend-hpa \
  -p '{"spec":{"maxReplicas":30}}'

# Verify
kubectl get hpa
```

---

#### 2.3 Add Memory-Based Scaling

```bash
# Edit HPA to add memory metric
kubectl edit hpa rag-backend-hpa

# Add this under spec.metrics:
#   - type: Resource
#     resource:
#       name: memory
#       target:
#         type: Utilization
#         averageUtilization: 80

# Or apply from file
cat <<EOF | kubectl apply -f -
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: rag-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rag-backend
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 120
EOF
```

---

### 3. Temporarily Disable Auto-Scaling

```bash
# Delete HPA (manual scaling only)
kubectl delete hpa rag-backend-hpa

# Manually set replicas
kubectl scale deployment rag-backend --replicas=5

# Re-enable auto-scaling later
kubectl apply -f k8s/hpa.yaml
```

---

## 📊 GKE Node Pool Scaling

### 1. View Node Pool Configuration

```bash
# List node pools
gcloud container node-pools list \
  --cluster=rag-chatbot-cluster \
  --region=us-central1

# Describe node pool
gcloud container node-pools describe default-pool \
  --cluster=rag-chatbot-cluster \
  --region=us-central1
```

---

### 2. Update Node Pool Auto-Scaling

```bash
# Update min/max nodes
gcloud container clusters update rag-chatbot-cluster \
  --enable-autoscaling \
  --min-nodes=2 \
  --max-nodes=15 \
  --region=us-central1

# Verify
gcloud container node-pools describe default-pool \
  --cluster=rag-chatbot-cluster \
  --region=us-central1 | grep -A 5 autoscaling
```

---

### 3. Add New Node Pool (Different Machine Type)

```bash
# Create high-memory node pool for large workloads
gcloud container node-pools create highmem-pool \
  --cluster=rag-chatbot-cluster \
  --machine-type=n1-highmem-4 \
  --num-nodes=0 \
  --enable-autoscaling \
  --min-nodes=0 \
  --max-nodes=5 \
  --region=us-central1

# Label nodes
gcloud container node-pools update highmem-pool \
  --cluster=rag-chatbot-cluster \
  --node-labels=workload=memory-intensive \
  --region=us-central1

# Deploy specific pods to this pool using nodeSelector
```

---

## 🧪 Scaling Tests

### 1. Baseline Load Test

```bash
# Test with normal load (100 concurrent users)
hey -n 5000 -c 100 -m POST \
  -H "Content-Type: application/json" \
  -d '{"question":"What is RAG?","top_k":3}' \
  http://${SERVICE_URL}/query

# Record metrics:
# - Average latency
# - p95 latency
# - Error rate
# - Replica count during test
```

---

### 2. Stress Test

```bash
# Test with high load (500 concurrent users)
hey -n 25000 -c 500 -m POST \
  -H "Content-Type: application/json" \
  -d '{"question":"What is RAG?","top_k":3}' \
  http://${SERVICE_URL}/query

# Monitor auto-scaling
watch kubectl get hpa
watch kubectl get pods -l app=rag-backend
watch kubectl top pods -l app=rag-backend
```

---

### 3. Sustained Load Test

```bash
# Test sustained load for 30 minutes
hey -n 100000 -c 200 -m POST \
  -H "Content-Type: application/json" \
  -d '{"question":"What is RAG?","top_k":3}' \
  http://${SERVICE_URL}/query

# Verify:
# - HPA scales up appropriately
# - HPA scales down after load decreases
# - No errors during scaling
```

---

## 📋 Scaling Decision Matrix

| Current CPU | Current Memory | Action | Target Replicas |
|-------------|----------------|--------|----------------|
| < 30% | < 40% | Scale down | Reduce by 30-50% |
| 30-50% | 40-60% | Maintain | No change |
| 50-70% | 60-80% | Monitor | No change (HPA will handle) |
| 70-85% | 80-90% | Pre-emptive scale | Increase by 30% |
| > 85% | > 90% | Emergency scale | Increase by 100% |

---

## ✅ Post-Scaling Verification

### Checklist

- [ ] All pods in Running state
- [ ] Health checks passing
- [ ] Readiness checks passing
- [ ] No CrashLoopBackOff pods
- [ ] Resource utilization appropriate (CPU < 70%, Memory < 80%)
- [ ] Error rate normal (< 1%)
- [ ] Latency acceptable (p95 < 2s)
- [ ] Load balanced across pods
- [ ] No resource exhaustion warnings

### Verification Commands

```bash
# Pod status
kubectl get pods -l app=rag-backend

# Health checks
kubectl exec -it <POD_NAME> -- curl localhost:8080/health

# Resource usage
kubectl top pods -l app=rag-backend

# Error rate
kubectl logs -l app=rag-backend --tail=500 | grep ERROR | wc -l

# Load balancing
kubectl logs -l app=rag-backend --tail=100 | grep "POST /query" | \
  awk '{print $1}' | sort | uniq -c
```

---

## 🚨 Troubleshooting

### Issue: Pods Not Scheduling (Insufficient Resources)

```bash
# Check pending pods
kubectl get pods | grep Pending

# Describe pending pod
kubectl describe pod <POD_NAME>

# Check node resources
kubectl describe nodes | grep -A 5 "Allocated resources"

# Solution: Add more nodes
gcloud container clusters resize rag-chatbot-cluster \
  --num-nodes 5 \
  --region us-central1
```

---

### Issue: HPA Not Scaling

```bash
# Check HPA status
kubectl get hpa
kubectl describe hpa rag-backend-hpa

# Common causes:
# 1. Metrics server not running
kubectl get deployment metrics-server -n kube-system

# 2. Resource requests not set
kubectl get deployment rag-backend -o yaml | grep -A 5 resources

# 3. CPU/Memory metrics not available
kubectl top pods -l app=rag-backend
```

---

### Issue: Scale-Down Too Aggressive

```bash
# Update HPA scale-down policy
kubectl patch hpa rag-backend-hpa -p '{
  "spec": {
    "behavior": {
      "scaleDown": {
        "stabilizationWindowSeconds": 600,
        "policies": [{
          "type": "Percent",
          "value": 25,
          "periodSeconds": 300
        }]
      }
    }
  }
}'
```

---

## 📅 Scaling Event Calendar

### Planned Scaling Events (2026)

| Date | Event | Expected Traffic | Action | Lead Time |
|------|-------|-----------------|--------|-----------|
| Feb 15 | Product Launch | +300% | Scale to 12 replicas | 1 day before |
| Mar 1 | Marketing Campaign | +200% | Scale to 9 replicas | 1 day before |
| Apr 10 | Conference Demo | +400% | Scale to 15 replicas | 2 days before |

---

## 🔗 Related Documentation

- [HPA Documentation](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [GKE Autoscaling](https://cloud.google.com/kubernetes-engine/docs/concepts/horizontalpodautoscaler)
- [SRE Runbook](../SRE_RUNBOOK.md)

---

**Last Updated**: February 2026  
**Maintained By**: SRE Team  
**Review Frequency**: Monthly
