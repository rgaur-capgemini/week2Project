# Week 3 Architecture Diagrams

## High-Level System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                                │
│                                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │   Login     │  │     Chat     │  │  Compliance  │  │   Admin    │ │
│  │ (OAuth 2.0) │  │  (RAG Chat)  │  │  Dashboard   │  │ Dashboard  │ │
│  └─────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
│                                            │                            │
└────────────────────────────────────────────┼────────────────────────────┘
                                             │
                          HTTPS (TLS 1.3)    │
                                             ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND (GKE)                              │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                    API ROUTES                                     │ │
│  │                                                                    │ │
│  │  /auth/*          - Authentication (JWT, OAuth)                  │ │
│  │  /api/query       - RAG Query (Week 1/2)                        │ │
│  │  /api/ingest      - Document Ingestion                          │ │
│  │  /history/*       - Chat History                                │ │
│  │  /analytics/*     - Usage Analytics                             │ │
│  │  /compliance/*    - Compliance Checking (NEW - Week 3)          │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                 │                                       │
│  ┌──────────────────────────────▼───────────────────────────────────┐ │
│  │              COMPLIANCE AGENTIC WORKFLOW (LangGraph)             │ │
│  │                                                                    │ │
│  │  ┌────────────┐   ┌────────────┐   ┌────────────┐               │ │
│  │  │ Template   │──>│  Matching  │──>│    Gap     │               │ │
│  │  │ Retrieval  │   │   Agent    │   │  Analysis  │               │ │
│  │  └────────────┘   └────────────┘   └────────────┘               │ │
│  │                            │                │                     │ │
│  │                            ▼                ▼                     │ │
│  │  ┌────────────┐   ┌────────────────────────────┐               │ │
│  │  │   Review   │<──│  Report Generation Agent   │               │ │
│  │  │   Agent    │   │      (Gemini 2.0)          │               │ │
│  │  └────────────┘   └────────────────────────────┘               │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │               EMAIL NOTIFICATION SERVICE                          │ │
│  │                    (SendGrid)                                     │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└──────────────┬───────────────────┬───────────────────┬─────────────────┘
               │                   │                   │
               ▼                   ▼                   ▼
┌──────────────────────┐ ┌───────────────────┐ ┌──────────────────────┐
│   Cloud Storage      │ │    Pub/Sub       │ │    Firestore         │
│                      │ │                   │ │                      │
│ • Documents          │ │ Topic:            │ │ Collections:         │
│ • Templates          │ │ template-         │ │ • compliance_reports │
│ • Reports            │ │ ingestion         │ │ • compliance_        │
│                      │ │                   │ │   templates          │
└──────────────────────┘ └─────────┬─────────┘ │ • rag_chunks         │
               │                   │            │ • chat_history       │
               │                   ▼            └──────────────────────┘
               │      ┌─────────────────────────┐
               │      │  Cloud Function (Gen2)  │
               │      │  template-processor     │
               │      │                         │
               │      │  • Download from GCS    │
               └─────>│  • Chunk + Embed        │
                      │  • Store metadata       │
                      └────────┬────────────────┘
                               │
                               ▼
                   ┌──────────────────────────┐
                   │  Vertex AI Services      │
                   │                          │
                   │  • Vector Search         │
                   │    (Templates + Docs)    │
                   │                          │
                   │  • Gemini 2.0 Flash      │
                   │    (Report Generation)   │
                   │                          │
                   │  • Text Embeddings       │
                   │    (text-embedding-004)  │
                   └──────────────────────────┘
```

## Compliance Workflow Detailed Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     USER UPLOADS DOCUMENT                            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  FastAPI Endpoint     │
                    │  POST /compliance/    │
                    │  documents/upload     │
                    └───────┬───────────────┘
                            │
                            ▼
                    ┌───────────────────────┐
                    │  1. Upload to GCS     │
                    │  2. Extract & Chunk   │
                    │  3. Store metadata    │
                    │     in Firestore      │
                    └───────┬───────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────────┐
        │   Background Task: Run Compliance Agent   │
        └───────┬───────────────────────────────────┘
                │
                ▼
        ┌───────────────────────────────────────────┐
        │     LangGraph Workflow Execution          │
        │                                            │
        │  NODE 1: Template Retrieval Agent         │
        │  ├─ Search vector store for templates     │
        │  ├─ Filter by template_type (optional)    │
        │  └─ Return top 10 relevant templates      │
        │                ↓                           │
        │  NODE 2: Matching Agent                   │
        │  ├─ Extract requirements from templates   │
        │  ├─ Chunk document into sections          │
        │  ├─ Compute embeddings                    │
        │  ├─ Calculate cosine similarity matrix    │
        │  └─ Match each requirement to best section│
        │                ↓                           │
        │  NODE 3: Gap Analysis Agent               │
        │  ├─ Identify missing requirements         │
        │  ├─ Calculate severity (high/med/low)     │
        │  ├─ Compute compliance score              │
        │  └─ Generate recommendations               │
        │                ↓                           │
        │  NODE 4: Report Generation Agent          │
        │  ├─ Build context from analysis           │
        │  ├─ Generate report via Gemini            │
        │  ├─ Format as professional Markdown       │
        │  └─ Extract key recommendations            │
        │                ↓                           │
        │  NODE 5: Review Agent                     │
        │  ├─ Check report completeness             │
        │  ├─ Validate sections present             │
        │  └─ Decide: refine or complete            │
        │                ↓                           │
        │  Decision: Iteration < 2?                 │
        │  ├─ Yes & needs refinement → Loop to NODE 4│
        │  └─ No or approved → Complete             │
        └───────┬───────────────────────────────────┘
                │
                ▼
        ┌───────────────────────────────────────────┐
        │   Update Firestore with Results           │
        │   • compliance_score                      │
        │   • report (Markdown)                     │
        │   • recommendations                       │
        │   • gaps (list with severity)             │
        │   • matched_sections                      │
        │   • status = "completed"                  │
        └───────┬───────────────────────────────────┘
                │
                ▼
        ┌───────────────────────────────────────────┐
        │   Send Email Notification (SendGrid)      │
        │   • Report ready message                  │
        │   • Compliance score                      │
        │   • Link to report                        │
        │   • Number of gaps                        │
        └───────────────────────────────────────────┘
                │
                ▼
        ┌───────────────────────────────────────────┐
        │   Frontend Auto-Polls for Updates         │
        │   (every 5 seconds while processing)      │
        └───────────────────────────────────────────┘
                │
                ▼
        ┌───────────────────────────────────────────┐
        │   User Views Completed Report             │
        │   • Score badge                           │
        │   • Gap details                           │
        │   • Recommendations                       │
        │   • Full Markdown report                  │
        └───────────────────────────────────────────┘
```

## Template Processing Flow (Cloud Function)

```
┌─────────────────────────────────────────────────────────────────────┐
│                  ADMIN UPLOADS TEMPLATE                              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  FastAPI Endpoint     │
                    │  POST /compliance/    │
                    │  templates/upload     │
                    └───────┬───────────────┘
                            │
                            ▼
                    ┌───────────────────────┐
                    │  1. Upload to GCS     │
                    │     (templates bucket)│
                    │  2. Create template_id│
                    └───────┬───────────────┘
                            │
                            ▼
                    ┌───────────────────────┐
                    │  Publish to Pub/Sub   │
                    │  Topic: compliance-   │
                    │  template-ingestion   │
                    │                       │
                    │  Message:             │
                    │  {                    │
                    │    template_id,       │
                    │    bucket,            │
                    │    blob_name,         │
                    │    template_type,     │
                    │    version            │
                    │  }                    │
                    └───────┬───────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────────┐
        │   Cloud Function Triggered                │
        │   (Gen2, VPC Connector)                   │
        └───────┬───────────────────────────────────┘
                │
                ▼
        ┌───────────────────────────────────────────┐
        │   1. Download Template from GCS           │
        │      • Parse blob_name from message       │
        │      • Download file content              │
        └───────┬───────────────────────────────────┘
                │
                ▼
        ┌───────────────────────────────────────────┐
        │   2. Chunk Template                       │
        │      • Extract text (PDF/DOCX/TXT)        │
        │      • Split into chunks (1000 words)     │
        │      • 200 word overlap                   │
        └───────┬───────────────────────────────────┘
                │
                ▼
        ┌───────────────────────────────────────────┐
        │   3. Generate Embeddings                  │
        │      • Use text-embedding-004             │
        │      • Batch process (5 at a time)        │
        │      • 768-dimensional vectors            │
        └───────┬───────────────────────────────────┘
                │
                ▼
        ┌───────────────────────────────────────────┐
        │   4. Add Metadata to Chunks               │
        │      • template_id                        │
        │      • template_type                      │
        │      • version                            │
        │      • is_template = true                 │
        │      • chunk_index                        │
        └───────┬───────────────────────────────────┘
                │
                ▼
        ┌───────────────────────────────────────────┐
        │   5. Store in Firestore                   │
        │                                            │
        │   Collection: compliance_templates        │
        │   Document: {template_id}                 │
        │   {                                        │
        │     template_id,                          │
        │     template_type,                        │
        │     version,                              │
        │     gcs_uri,                              │
        │     chunk_count,                          │
        │     status: "ready"                       │
        │   }                                        │
        │                                            │
        │   Collection: compliance_template_chunks  │
        │   Documents: {template_id}_chunk_{i}      │
        │   {                                        │
        │     template_id,                          │
        │     chunk_index,                          │
        │     text,                                 │
        │     metadata,                             │
        │     embedding: [768 floats]               │
        │   }                                        │
        └───────┬───────────────────────────────────┘
                │
                ▼
        ┌───────────────────────────────────────────┐
        │   6. (Optional) Send Email Notification   │
        │      • Template processed successfully    │
        │      • Chunk count                        │
        └───────────────────────────────────────────┘
                │
                ▼
        ┌───────────────────────────────────────────┐
        │   Template Ready for Use                  │
        │   • Available in vector search            │
        │   • Can be used for compliance checks     │
        └───────────────────────────────────────────┘
```

## Data Flow Diagram

```
┌──────────────┐
│   DOCUMENT   │
│   (Upload)   │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐     ┌─────────────────────┐
│   GCS Storage        │────>│  Firestore          │
│   • Raw document     │     │  • Document metadata│
│   • Timestamped path │     │  • Status tracking  │
└──────────────────────┘     └─────────────────────┘
       │
       ▼
┌──────────────────────┐
│   Chunking           │
│   • Extract text     │
│   • Split into chunks│
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐     ┌─────────────────────┐
│   Embeddings         │────>│  Vector Search      │
│   • text-embedding-  │     │  • 768-dim vectors  │
│     004              │     │  • Similarity search│
└──────────────────────┘     └──────┬──────────────┘
                                    │
       ┌────────────────────────────┘
       │
       ▼
┌──────────────────────┐     ┌─────────────────────┐
│   Template Matching  │────>│  Gap Analysis       │
│   • Cosine similarity│     │  • Score calculation│
│   • Threshold: 0.75  │     │  • Severity levels  │
└──────────────────────┘     └──────┬──────────────┘
                                    │
                                    ▼
                          ┌─────────────────────┐
                          │  Gemini 2.0 Flash   │
                          │  • Report generation│
                          │  • Recommendations  │
                          └──────┬──────────────┘
                                 │
                                 ▼
                          ┌─────────────────────┐
                          │  Firestore          │
                          │  • Complete report  │
                          │  • Score & gaps     │
                          │  • Status: completed│
                          └──────┬──────────────┘
                                 │
                                 ▼
                          ┌─────────────────────┐
                          │  Email Notification │
                          │  (SendGrid)         │
                          └─────────────────────┘
```

## Component Interaction Matrix

```
┌─────────────────┬─────────┬──────────┬───────────┬─────────┬──────────┐
│   Component     │   GCS   │ Firestore│  Vertex AI│  Pub/Sub│ SendGrid │
├─────────────────┼─────────┼──────────┼───────────┼─────────┼──────────┤
│ FastAPI Backend │  Write  │  R/W     │  Query    │ Publish │  Send    │
│                 │  (docs) │          │ (embed)   │         │          │
├─────────────────┼─────────┼──────────┼───────────┼─────────┼──────────┤
│ Cloud Function  │  Read   │  Write   │  Query    │ Subscribe│  Send    │
│                 │(template│          │ (embed)   │         │          │
├─────────────────┼─────────┼──────────┼───────────┼─────────┼──────────┤
│ Compliance      │   -     │  Read    │  Query    │   -     │   -      │
│ Agent           │         │          │(vector srch│         │          │
├─────────────────┼─────────┼──────────┼───────────┼─────────┼──────────┤
│ Frontend        │   -     │   -      │    -      │   -     │   -      │
│                 │         │(via API) │           │         │          │
└─────────────────┴─────────┴──────────┴───────────┴─────────┴──────────┘

Legend:
  R/W = Read and Write
  -   = No direct interaction (uses API)
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      SECURITY LAYERS                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Layer 1: Authentication                                            │
│  ├─ Google OAuth 2.0 (ID token validation)                         │
│  ├─ JWT tokens (access + refresh)                                  │
│  └─ Token expiration (1 hour access, 7 days refresh)               │
│                                                                      │
│  Layer 2: Authorization (RBAC)                                      │
│  ├─ Roles: admin, user, guest                                      │
│  ├─ Permissions:                                                    │
│  │   • DOCUMENT_UPLOAD                                             │
│  │   • DOCUMENT_VIEW_OWN                                           │
│  │   • DOCUMENT_DELETE_OWN                                         │
│  │   • ADMIN_MANAGE_SYSTEM                                         │
│  └─ Role-Permission Matrix enforcement                             │
│                                                                      │
│  Layer 3: Data Isolation                                            │
│  ├─ User ID filtering in Firestore queries                         │
│  ├─ GCS object-level permissions                                   │
│  └─ Admin bypass (can view all reports)                            │
│                                                                      │
│  Layer 4: API Security                                              │
│  ├─ Rate limiting (60 req/min per IP)                              │
│  ├─ Request size limits (10MB default)                             │
│  ├─ CORS policy (configurable origins)                             │
│  └─ Security headers (HSTS, CSP, X-Frame-Options)                  │
│                                                                      │
│  Layer 5: Service-to-Service                                        │
│  ├─ Service accounts with minimal permissions                      │
│  ├─ Secret Manager for API keys                                    │
│  ├─ VPC connector for Cloud Function                               │
│  └─ Private GKE cluster (optional)                                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

**Legend:**
- → Direct call/data flow
- ──> Asynchronous processing
- ├─ Component/step
- └─ Final step/output
