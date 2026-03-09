# Week 5 Quick Start Guide

## 🚀 Deploy Everything in 5 Minutes

### Prerequisites
- GCP Project: `botpproject`
- GKE Cluster: `chatbot-rag-gke` (already deployed)
- Kubectl configured
- gcloud CLI authenticated

---

## Step 1: Deploy via CI/CD (1 command)

```bash
cd week3_btoproject_cloudrun_full
gcloud builds submit --config cloudbuild-gke.yaml
```

**This will**:
- Run tests
- Build Docker image
- Deploy CSV processor Cloud Function
- Create GCS buckets
- Update GKE deployment
- Run smoke tests

**Wait time**: ~10-15 minutes

---

## Step 2: Get Backend IP

```bash
kubectl get svc backend -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

Save this IP as `BACKEND_IP`.

---

## Step 3: Test Agent (Calculator Example)

```bash
curl -X POST http://$BACKEND_IP:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Calculate 25 * 4 + 100",
    "session_id": "quick-test"
  }'
```

**Expected Output**:
```json
{
  "answer": "The result is 200",
  "session_id": "quick-test",
  "iterations": 1,
  "execution_trace": [
    {
      "tool": "calculator",
      "args": {"expression": "25 * 4 + 100"},
      "result": 200
    }
  ]
}
```

---

## Step 4: Test Multimodal (Image Upload)

```bash
# Upload an image
curl -X POST http://$BACKEND_IP:8000/multimodal/images/upload \
  -F "file=@/path/to/image.jpg" \
  -F "description=Beautiful sunset" \
  -F "tags=nature,sunset"
```

**Expected Output**:
```json
{
  "image_id": "abc-123-def",
  "gcs_uri": "gs://botpproject-images/images/abc-123-def/image.jpg",
  "public_url": "https://storage.googleapis.com/...",
  "filename": "image.jpg",
  "message": "Image uploaded and indexed successfully"
}
```

---

## Step 5: Test CSV Ingestion

```bash
# 1. Create sample CSV
cat > sample.csv << EOF
name,age,city
Alice,30,New York
Bob,25,San Francisco
Charlie,35,Seattle
EOF

# 2. Upload to GCS
gsutil cp sample.csv gs://botpproject-csv-uploads/

# 3. Wait 10 seconds for Cloud Function

# 4. Query via agent
curl -X POST http://$BACKEND_IP:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Query the sample table and show all rows",
    "session_id": "csv-test"
  }'
```

---

## 🎯 Available Agent Tools

```bash
curl http://$BACKEND_IP:8000/agent/tools
```

**Output**:
```json
[
  {
    "name": "rag_search",
    "description": "Search the knowledge base..."
  },
  {
    "name": "calculator",
    "description": "Perform mathematical calculations..."
  },
  {
    "name": "csv_query",
    "description": "Query CSV data from BigQuery..."
  },
  {
    "name": "image_analysis",
    "description": "Analyze images with Gemini Vision..."
  },
  {
    "name": "web_search",
    "description": "Search the internet..."
  }
]
```

---

## 📊 Check Deployment Status

### GKE Deployment
```bash
kubectl get deployment backend
kubectl get pods -l app=backend
```

### Cloud Function
```bash
gcloud functions describe csv-processor --region=us-central1
```

### GCS Buckets
```bash
gsutil ls gs://botpproject-csv-uploads
gsutil ls gs://botpproject-images
```

### BigQuery Dataset
```bash
bq ls botpproject:csv_data
```

---

## 🧪 More Examples

### Example 1: RAG Search
```bash
curl -X POST http://$BACKEND_IP:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Search the knowledge base for information about OAuth",
    "session_id": "rag-test"
  }'
```

### Example 2: Complex Calculation
```bash
curl -X POST http://$BACKEND_IP:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Calculate (10 + 5) ** 2 - 50",
    "session_id": "calc-test"
  }'
```

### Example 3: Image Analysis
```bash
# First upload an image and get the gcs_uri
IMAGE_URI="gs://botpproject-images/images/abc-123/photo.jpg"

curl -X POST http://$BACKEND_IP:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"Analyze the image at $IMAGE_URI\",
    \"session_id\": \"vision-test\"
  }"
```

### Example 4: Multimodal Text Search
```bash
curl -X POST http://$BACKEND_IP:8000/multimodal/search/text \
  -H "Content-Type: application/json" \
  -d '{
    "query": "sunset over mountains",
    "top_k": 5
  }'
```

---

## 🔍 View Logs

### Backend Logs
```bash
kubectl logs -l app=backend --tail=100 -f
```

### Cloud Function Logs
```bash
gcloud functions logs read csv-processor --region=us-central1 --limit=50
```

### Cloud Build Logs
```bash
gcloud builds list --limit=5
gcloud builds log <BUILD_ID>
```

---

## 📱 Access Swagger UI

Open in browser:
```
http://<BACKEND_IP>:8000/docs
```

Navigate to:
- `/agent` endpoints
- `/multimodal` endpoints

Try the interactive API!

---

## 🛠️ Troubleshooting

### Backend not responding
```bash
# Check pod status
kubectl get pods -l app=backend

# Check logs
kubectl logs -l app=backend --tail=50

# Restart deployment
kubectl rollout restart deployment/backend
```

### Cloud Function not triggering
```bash
# Check function status
gcloud functions describe csv-processor --region=us-central1

# Check logs
gcloud functions logs read csv-processor --region=us-central1

# Redeploy
cd cloud-functions/csv-processor
gcloud functions deploy csv-processor --gen2 ...
```

### GCS bucket doesn't exist
```bash
# Create manually
gsutil mb -p botpproject -l us-central1 gs://botpproject-csv-uploads
gsutil mb -p botpproject -l us-central1 gs://botpproject-images
```

---

## 🎉 Success Criteria

✅ All checks pass:
```bash
# 1. Agent responds
curl http://$BACKEND_IP:8000/agent/tools

# 2. Multimodal responds
curl http://$BACKEND_IP:8000/multimodal/images

# 3. Calculator works
curl -X POST http://$BACKEND_IP:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Calculate 2+2", "session_id": "test"}'

# 4. CSV function exists
gcloud functions describe csv-processor --region=us-central1

# 5. Buckets exist
gsutil ls gs://botpproject-csv-uploads
gsutil ls gs://botpproject-images
```

If all 5 commands succeed: **Week 5 is fully deployed! 🎉**

---

## 📚 Next Steps

1. **Test all 5 tools**:
   - rag_search
   - calculator ✅ (tested above)
   - csv_query
   - image_analysis
   - web_search (requires API key)

2. **Upload more images**:
   - Build image gallery
   - Test text-to-image search
   - Test image-to-image search

3. **Ingest CSV data**:
   - Upload business data
   - Query via agent
   - Build dashboards

4. **Monitor performance**:
   - Check Firestore usage
   - Monitor GCS storage
   - Track BigQuery costs

---

## 📞 Support

- **Logs**: `kubectl logs -l app=backend`
- **Docs**: http://<BACKEND_IP>:8000/docs
- **Status**: http://<BACKEND_IP>:8000/health

---

**Deploy time**: 10-15 minutes  
**Test time**: 5 minutes  
**Total**: ~20 minutes to full Week 5 deployment! 🚀
