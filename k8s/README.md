# Kubernetes Manifests for RAG Chatbot

This directory contains all Kubernetes manifests needed to deploy the RAG chatbot application to GKE.

## Prerequisites

1. **GKE Cluster**: Create a GKE cluster with Workload Identity enabled
   ```bash
   gcloud container clusters create rag-chatbot-cluster \
     --region=us-central1 \
     --enable-ip-alias \
     --workload-pool=btoproject-486405-486604.svc.id.goog \
     --enable-autoscaling \
     --min-nodes=1 \
     --max-nodes=10 \
     --machine-type=n1-standard-2
   ```

2. **Workload Identity Setup**:
   ```bash
   # Create GCP service accounts
   gcloud iam service-accounts create rag-backend-sa \
     --display-name="RAG Backend Service Account"
   
   # Grant permissions
   gcloud projects add-iam-policy-binding btoproject-486405-486604 \
     --member="serviceAccount:rag-backend-sa@btoproject-486405-486604.iam.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   
   gcloud projects add-iam-policy-binding btoproject-486405-486604 \
     --member="serviceAccount:rag-backend-sa@btoproject-486405-486604.iam.gserviceaccount.com" \
     --role="roles/aiplatform.user"
   
   gcloud projects add-iam-policy-binding btoproject-486405-486604 \
     --member="serviceAccount:rag-backend-sa@btoproject-486405-486604.iam.gserviceaccount.com" \
     --role="roles/storage.objectAdmin"
   
   gcloud projects add-iam-policy-binding btoproject-486405-486604 \
     --member="serviceAccount:rag-backend-sa@btoproject-486405-486604.iam.gserviceaccount.com" \
     --role="roles/datastore.user"
   
   # Bind Kubernetes SA to GCP SA
   gcloud iam service-accounts add-iam-policy-binding \
     rag-backend-sa@btoproject-486405-486604.iam.gserviceaccount.com \
     --role=roles/iam.workloadIdentityUser \
     --member="serviceAccount:btoproject-486405-486604.svc.id.goog[default/rag-backend-sa]"
   ```

3. **Create Secrets in Secret Manager**:
   ```bash
   echo -n "your-redis-password" | gcloud secrets create redis-password --data-file=-
   echo -n "your-google-oauth-client-id" | gcloud secrets create google-oauth-client-id --data-file=-
   echo -n "your-google-oauth-client-secret" | gcloud secrets create google-oauth-client-secret --data-file=-
   ```

4. **Container Images**: Build and push images to GCR
   ```bash
   # Build backend
   docker build -t gcr.io/btoproject-486405-486604/rag-backend:latest .
   docker push gcr.io/btoproject-486405-486604/rag-backend:latest
   
   # Build frontend
   docker build -t gcr.io/btoproject-486405-486604/rag-frontend:latest -f frontend/Dockerfile frontend/
   docker push gcr.io/btoproject-486405-486604/rag-frontend:latest
   ```

## Deployment Order

Deploy resources in the following order:

```bash
# 1. Get cluster credentials
gcloud container clusters get-credentials rag-chatbot-cluster --region=us-central1

# 2. Create namespace (optional)
kubectl create namespace rag-chatbot
kubectl config set-context --current --namespace=rag-chatbot

# 3. Deploy service accounts with Workload Identity
kubectl apply -f service-account.yaml

# 4. Deploy ConfigMap
kubectl apply -f configmap.yaml

# 5. Deploy backend
kubectl apply -f backend-deployment.yaml
kubectl apply -f backend-service.yaml

# 6. Deploy frontend
kubectl apply -f frontend-deployment.yaml
kubectl apply -f frontend-service.yaml

# 7. Deploy autoscaling
kubectl apply -f hpa.yaml

# 8. Deploy network policies
kubectl apply -f network-policy.yaml

# 9. Deploy ingress (optional - for custom domain)
kubectl apply -f ingress.yaml
```

## Quick Deploy All

```bash
kubectl apply -f k8s/
```

## Verification

```bash
# Check deployments
kubectl get deployments

# Check pods
kubectl get pods

# Check services
kubectl get services

# Get external IPs
kubectl get service rag-backend -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
kubectl get service rag-frontend -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Check logs
kubectl logs -l app=rag-backend --tail=100 -f
kubectl logs -l app=rag-frontend --tail=100 -f
```

## Scaling

```bash
# Manual scaling
kubectl scale deployment rag-backend --replicas=5

# View HPA status
kubectl get hpa
kubectl describe hpa rag-backend-hpa
```

## Updates

```bash
# Update image
kubectl set image deployment/rag-backend rag-backend=gcr.io/btoproject-486405-486604/rag-backend:v1.2.0

# Rollback
kubectl rollout undo deployment/rag-backend

# Check rollout status
kubectl rollout status deployment/rag-backend
```

## Troubleshooting

```bash
# Describe pod
kubectl describe pod <pod-name>

# View events
kubectl get events --sort-by=.metadata.creationTimestamp

# Check service endpoints
kubectl get endpoints

# Port forward for debugging
kubectl port-forward service/rag-backend 8080:80
```

## Cleanup

```bash
kubectl delete -f k8s/
```

## Files Description

- **backend-deployment.yaml**: Backend deployment with 3 replicas, health checks, resource limits
- **backend-service.yaml**: LoadBalancer service for backend on port 80
- **frontend-deployment.yaml**: Frontend deployment with 2 replicas
- **frontend-service.yaml**: LoadBalancer service for frontend on port 80
- **configmap.yaml**: Non-sensitive configuration (GCP project, models, Redis host)
- **service-account.yaml**: Kubernetes service accounts with Workload Identity annotations
- **hpa.yaml**: Horizontal Pod Autoscaler for automatic scaling based on CPU/memory
- **ingress.yaml**: Google Cloud Load Balancer with SSL certificate
- **network-policy.yaml**: Network policies for pod-to-pod communication security

## CI/CD Integration

The `cloudbuild-gke.yaml` pipeline automatically:
1. Builds Docker images
2. Runs tests and security scans
3. Pushes images to GCR
4. Deploys to GKE using `kubectl set image`
5. Waits for rollout completion
6. Runs smoke tests

To trigger the pipeline:
```bash
gcloud builds submit --config=ci/cloudbuild-gke.yaml
```

Or set up a Cloud Build trigger connected to your Git repository.
