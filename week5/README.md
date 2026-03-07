# Week 5 – Agentic AI, Multimodal & CI/CD

## Overview

Week 5 extends the existing RAG service with four major features on top of the Week 1–4 production stack:

| Feature | Description |
|---|---|
| **Agentic AI** | Multi-agent system using Google ADK + Gemini function-calling |
| **CSV Ingestion** | Cloud Function that ingests CSVs into GCS and embeds them into Vector Search |
| **Enhanced RAG** | Query decomposition, reranking, self-evaluation, source diversity |
| **Multimodal** | Gemini Vision: OCR, Visual Q&A, chart analysis, table extraction |
| **CI/CD Pipeline** | Cloud Build with canary deployments and automated smoke tests |

---

## Folder Structure

```
week5/
├── agentic_ai/
│   ├── agent.py              # RAGAgent – Gemini function-calling agentic loop
│   ├── tools.py              # AgentToolkit – 5 tool implementations
│   └── orchestrator.py       # MultiAgentOrchestrator – intent routing
│
├── cloud_functions/
│   └── csv_ingestor/
│       ├── main.py           # HTTP Cloud Function entry point
│       └── requirements.txt  # Runtime deps for the function
│
├── rag/
│   ├── csv_embedder.py       # CSV → text chunks → Vertex AI Vector Search
│   └── enhanced_rag_pipeline.py  # Query decomposition + self-eval RAG
│
├── multimodal/
│   ├── image_processor.py    # OCR, describe, classify, table extraction
│   └── multimodal_pipeline.py # Image + RAG combined pipeline
│
├── api/
│   ├── schemas.py            # Pydantic request/response models
│   ├── agent_routes.py       # /api/v5/agent/* endpoints
│   └── multimodal_routes.py  # /api/v5/multimodal/* endpoints
│
├── ci_cd/
│   ├── cloudbuild.yaml       # Full CI/CD pipeline (build → test → canary → prod)
│   └── deploy.sh             # Manual deployment script
│
└── tests/
    ├── test_agent.py         # Agent + orchestrator + toolkit tests
    ├── test_csv_ingestor.py  # Cloud Function + CSVEmbedder tests
    └── test_multimodal.py    # ImageProcessor + MultimodalPipeline tests
```

---

## Feature 1 – Agentic AI (Google ADK + Gemini)

### Architecture

```
User Query
    ↓
MultiAgentOrchestrator  (intent classification)
    ↓
RAGAgent  (Gemini function-calling loop)
    ↓
┌──────────────┬───────────────┬──────────────┬──────────────┬──────────────┐
│search_docs   │ analyze_csv   │summarize_doc │process_image │get_cost_sum  │
│(Vector AI)   │(GCS/Pandas)   │(GCS+Gemini)  │(GeminiVision)│(FinOps)      │
└──────────────┴───────────────┴──────────────┴──────────────┴──────────────┘
    ↓ tool results
Gemini LLM (final synthesis)
    ↓
Structured Answer + Sources + Tool Call Log
```

### API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v5/agent/query` | Single agentic query |
| `POST` | `/api/v5/agent/batch` | Batch queries (up to 20) |
| `POST` | `/api/v5/agent/csv/embed` | Trigger CSV embedding (background) |
| `GET` | `/api/v5/agent/health` | Service health |
| `POST` | `/api/v5/rag/query` | Enhanced RAG with decomposition |

### Example Request

```bash
curl -X POST https://<service-url>/api/v5/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key trends in our Q4 sales CSV?",
    "session_id": "sess_abc123",
    "metadata": {"gcs_uri": "gs://my-bucket/q4_sales.csv"}
  }'
```

---

## Feature 2 – CSV Ingestion (Cloud Function)

### Flow

```
HTTP POST (CSV file or gcs_uri)
    ↓
Cloud Function (csv_ingestor)
    ↓
Validate CSV (rows, columns, nulls)
    ↓
Upload to GCS (gs://<project>-csv-data/csv-ingest/<date>/<filename>)
    ↓
Pub/Sub publish → "csv-ingestion-topic"
    ↓
CSVEmbedder (background) → Vertex AI Vector Search
```

### Deploy the Cloud Function

```bash
gcloud functions deploy csv-ingestor \
  --gen2 \
  --runtime=python311 \
  --region=us-central1 \
  --source=week5/cloud_functions/csv_ingestor/ \
  --entry-point=csv_ingestor \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars="PROJECT_ID=btoproject-486405-486604,\
GCS_CSV_BUCKET=btoproject-486405-486604-csv-data,\
PUBSUB_TOPIC=csv-ingestion-topic"
```

### Test the Function

```bash
# Upload a CSV file
curl -X POST https://<FUNCTION_URL> \
  -F "file=@sales_data.csv"

# Reference an existing GCS file
curl -X POST https://<FUNCTION_URL> \
  -H "Content-Type: application/json" \
  -d '{"gcs_uri": "gs://my-bucket/data.csv"}'
```

---

## Feature 3 – Enhanced RAG

Improvements over Week 1–4 RAG:

| Feature | Description |
|---|---|
| Query decomposition | Complex questions → 2–4 sub-queries |
| Multi-hop retrieval | Run vector search for each sub-query |
| Source diversity | Max 3 chunks per source document |
| Hybrid reranking | Re-score chunks with HybridReranker |
| Self-evaluation | Gemini rates faithfulness, relevance, hallucination risk |
| CSV-aware chunks | CSV rows embedded alongside document chunks |

### Example Request

```bash
curl -X POST https://<service-url>/api/v5/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What compliance requirements apply to our EU customer data handling?",
    "enable_decomposition": true,
    "enable_self_eval": true
  }'
```

---

## Feature 4 – Multimodal (Gemini Vision)

### Supported Operations

| Task | Description |
|---|---|
| `describe` | Generate a description of image content |
| `ocr` | Extract all visible text |
| `qa` | Answer a specific question about the image |
| `table` | Extract table/spreadsheet data as JSON/CSV |
| `classify` | Classify into predefined categories |

### API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v5/multimodal/query` | Image(s) + RAG query (GCS/HTTP URLs) |
| `POST` | `/api/v5/multimodal/upload` | Upload image files directly |
| `POST` | `/api/v5/multimodal/ocr` | Batch OCR multiple images |
| `POST` | `/api/v5/multimodal/describe` | Describe images |
| `POST` | `/api/v5/multimodal/invoice` | Invoice extraction |
| `POST` | `/api/v5/multimodal/chart` | Chart analysis + RAG correlation |
| `GET` | `/api/v5/multimodal/health` | Service health |

### Example Requests

```bash
# Analyse a chart image
curl -X POST https://<service-url>/api/v5/multimodal/chart \
  -H "Content-Type: application/json" \
  -d '{
    "image_source": "gs://my-bucket/q4_chart.png",
    "question": "What is the YoY growth trend?"
  }'

# Upload an invoice for OCR
curl -X POST https://<service-url>/api/v5/multimodal/upload \
  -F "question=Extract all invoice details" \
  -F "image_task=ocr" \
  -F "files=@invoice.jpg"
```

---

## Feature 5 – CI/CD Pipeline (Cloud Build)

### Pipeline Stages

```
push to main
    ↓
1. Install dependencies
2. Lint (flake8)
3. Unit tests (pytest + coverage)
4. Docker build + push to Artifact Registry
5. Deploy CSV Cloud Function
6. Deploy Cloud Run canary (0% traffic)
7. Smoke tests against canary
8. Shift 10% traffic to canary
9. Promote canary to 100% production
10. Send Pub/Sub build notification
```

### Trigger CI/CD

```bash
# Submit a build manually
gcloud builds submit \
  --config=week5/ci_cd/cloudbuild.yaml \
  --substitutions="_ENV=production,_CANARY_PERCENT=10"

# Or use the deploy script
chmod +x week5/ci_cd/deploy.sh
./week5/ci_cd/deploy.sh production all
```

---

## Running Tests

```bash
# Run all Week 5 tests
pytest week5/tests/ -v --tb=short

# Run with coverage
pytest week5/tests/ --cov=week5 --cov-report=term-missing

# Run specific test file
pytest week5/tests/test_agent.py -v
pytest week5/tests/test_csv_ingestor.py -v
pytest week5/tests/test_multimodal.py -v
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PROJECT_ID` | `btoproject-486405-486604` | GCP project |
| `REGION` | `us-central1` | GCP region |
| `MODEL_VARIANT` | `gemini-2.0-flash-001` | Gemini model |
| `GCS_CSV_BUCKET` | `<project>-csv-data` | Bucket for CSV files |
| `PUBSUB_TOPIC` | `csv-ingestion-topic` | Topic for CSV events |

---

## Dependencies Added (requirements.txt)

| Package | Purpose |
|---|---|
| `google-adk>=0.1.0` | Google Agent Development Kit |
| `Pillow==10.4.0` | Image handling |
| `pandas==2.2.2` | CSV analysis |
| `functions-framework==3.8.1` | Cloud Function local dev |
