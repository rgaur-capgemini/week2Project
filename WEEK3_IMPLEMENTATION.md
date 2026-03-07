# Week 3 Implementation: Compliance Report Generation System

## Overview

Week 3 adds an **Agentic Compliance Report Generation System** to the existing RAG chatbot. This system uses LangGraph to orchestrate multiple AI agents that analyze documents against compliance templates and generate detailed reports.

## New Features Implemented

### 1. **Agentic Multi-Node Architecture** ✅
- **File**: [`app/compliance/agents.py`](app/compliance/agents.py)
- **Technology**: LangGraph
- **Workflow**:
  1. **Template Retrieval Agent** - Finds relevant compliance templates from vector store
  2. **Matching Agent** - Matches document sections to template requirements using semantic similarity
  3. **Gap Analysis Agent** - Identifies missing/non-compliant sections
  4. **Report Generation Agent** - Creates professional compliance reports using Gemini
  5. **Review Agent** - Self-checks and optionally refines the report

### 2. **Template Management System** ✅
- **Template Matcher**: [`app/compliance/template_matcher.py`](app/compliance/template_matcher.py)
  - Semantic similarity matching between document sections and template requirements
  - Configurable similarity threshold (default: 0.75)
  - Cosine similarity computation
  
- **Gap Analyzer**: [`app/compliance/gap_analyzer.py`](app/compliance/gap_analyzer.py)
  - Identifies compliance gaps with severity levels (high, medium, low)
  - Calculates overall compliance score
  - Generates actionable recommendations
  
- **Report Generator**: [`app/compliance/report_generator.py`](app/compliance/report_generator.py)
  - Uses Gemini LLM to create professional Markdown reports
  - Includes executive summary, gap analysis, and recommendations
  - Fallback report generation if LLM fails

### 3. **Pub/Sub Integration + Cloud Functions** ✅
- **Cloud Function**: [`cloud-functions/template-processor/`](cloud-functions/template-processor/)
  - Triggered by Pub/Sub when templates are uploaded
  - Chunks templates, generates embeddings, stores in vector search
  - Stores metadata in Firestore
  
- **Pub/Sub Topic**: `compliance-template-ingestion`
- **Deployment**:
  ```bash
  cd cloud-functions/template-processor
  gcloud functions deploy compliance-template-processor \
    --gen2 \
    --region=us-central1 \
    --runtime=python311 \
    --trigger-topic=compliance-template-ingestion
  ```

### 4. **Backend API Endpoints** ✅
- **File**: [`app/compliance_routes.py`](app/compliance_routes.py)

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/compliance/documents/upload` | POST | Upload document for compliance check | DOCUMENT_UPLOAD |
| `/compliance/reports/{report_id}` | GET | Get detailed compliance report | DOCUMENT_VIEW_OWN |
| `/compliance/reports` | GET | List all reports for user | DOCUMENT_VIEW_OWN |
| `/compliance/templates/upload` | POST | Upload compliance template (admin) | ADMIN_MANAGE_SYSTEM |
| `/compliance/reports/{report_id}` | DELETE | Delete compliance report | DOCUMENT_DELETE_OWN |

### 5. **Email Notifications** ✅
- **File**: [`app/notifications/email_service.py`](app/notifications/email_service.py)
- **Provider**: SendGrid
- **Notifications**:
  - Compliance report ready (with score, gaps, link to report)
  - Template processing complete
- **Configuration**: Set `SENDGRID_API_KEY` environment variable

### 6. **Frontend Components** ✅

#### Compliance Dashboard
- **File**: [`frontend/src/app/components/compliance.component.ts`](frontend/src/app/components/compliance.component.ts)
- **Features**:
  - Document upload form with template type selection
  - Reports list table with score, gaps, status
  - Color-coded compliance scores
  - Filter by template type (ISO27001, GDPR, HIPAA, etc.)

#### Compliance Report Viewer
- **File**: [`frontend/src/app/components/compliance-report.component.ts`](frontend/src/app/components/compliance-report.component.ts)
- **Features**:
  - Score badge with color coding
  - Recommendations list
  - Expandable gaps with severity levels
  - Full Markdown report rendering
  - Auto-polling for processing reports (5s interval)
  - Download report as Markdown

#### Compliance Service
- **File**: [`frontend/src/app/services/compliance.service.ts`](frontend/src/app/services/compliance.service.ts)
- **Methods**:
  - `uploadDocument(file, templateType)`
  - `uploadTemplate(file, templateType, version)`
  - `getReports(limit, offset)`
  - `getReport(reportId)`
  - `deleteReport(reportId)`

### 7. **Security & Authentication** ✅
- Integrated with existing JWT + RBAC system
- Permissions:
  - `DOCUMENT_UPLOAD` - Upload documents for compliance check
  - `DOCUMENT_VIEW_OWN` - View own compliance reports
  - `DOCUMENT_DELETE_OWN` - Delete own reports
  - `ADMIN_MANAGE_SYSTEM` - Upload compliance templates
- User isolation - users can only see their own reports (except admins)

### 8. **Storage Integration** ✅
- **GCS**: Document and template storage
  - Bucket: `{PROJECT_ID}-compliance-templates`
  - Path structure: `templates/{template_type}/{template_id}/{filename}`
  
- **Firestore**: Metadata and report storage
  - Collection: `compliance_reports` - Report metadata and results
  - Collection: `compliance_templates` - Template metadata
  - Collection: `compliance_template_chunks` - Template chunks with embeddings
  
- **Vertex AI Vector Search**: Template embeddings
  - Uses existing index from Week 1/2
  - Metadata field `is_template=true` to distinguish templates

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Angular Frontend                          │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │ Compliance   │  │ Compliance Report│  │ Navbar       │ │
│  │ Dashboard    │  │ Viewer           │  │ (+ link)     │ │
│  └──────────────┘  └──────────────────┘  └──────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (GKE)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ compliance_routes.py - 5 new endpoints                │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                             │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │ ComplianceAgent (LangGraph)                           │  │
│  │  ├─ Template Retrieval Agent                          │  │
│  │  ├─ Matching Agent (TemplateMatcher)                  │  │
│  │  ├─ Gap Analysis Agent (GapAnalyzer)                  │  │
│  │  ├─ Report Generation Agent (ReportGenerator)         │  │
│  │  └─ Review Agent                                       │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                             │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │ EmailService (SendGrid) - Notifications              │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
             ▼                                ▼
┌─────────────────────────┐    ┌──────────────────────────────┐
│ GCS                     │    │ Pub/Sub Topic               │
│ - Documents             │    │ compliance-template-ingestion│
│ - Templates             │    └────────────┬─────────────────┘
└─────────────────────────┘                 │
             │                              ▼
             │                 ┌──────────────────────────────┐
             │                 │ Cloud Function (Gen2)       │
             │                 │ template-processor           │
             │                 │  - Download from GCS        │
             │                 │  - Chunk + Embed            │
             │                 │  - Store in Vector Store    │
             │                 └────────────┬─────────────────┘
             │                              │
             ▼                              ▼
┌─────────────────────────┐    ┌──────────────────────────────┐
│ Firestore               │    │ Vertex AI Vector Search     │
│ - compliance_reports    │    │ - Template embeddings       │
│ - compliance_templates  │    │ - Document embeddings       │
│ - chunks                │    │ (is_template metadata flag) │
└─────────────────────────┘    └─────────────────────────────┘
```

## Usage Guide

### For End Users

#### 1. Check Document Compliance

1. Navigate to **Compliance** tab in the navbar
2. Click **Select Document** and choose a file (PDF, DOCX, TXT)
3. Optionally select a **Template Type** (ISO27001, GDPR, etc.)
4. Click **Check Compliance**
5. Wait for processing (typically 30-60 seconds)
6. View the generated report with:
   - Compliance score (0-100%)
   - Identified gaps with severity levels
   - Actionable recommendations
   - Full detailed report

#### 2. View Past Reports

1. Go to **Compliance** tab
2. View list of all your reports
3. Click **View** icon to see full report
4. Click **Delete** icon to remove a report
5. Reports show:
   - Document ID
   - Compliance score (color-coded)
   - Number of gaps
   - Status (processing, completed, failed)
   - Creation date

#### 3. Download Report

1. Open a completed report
2. Click **Download Report** button
3. Report is saved as Markdown file

### For Administrators

#### 1. Upload Compliance Template

1. Navigate to **Compliance** tab
2. Use the **Upload Template** section (admin only)
3. Select template file
4. Enter **Template Type** (e.g., "ISO27001")
5. Enter **Version** (e.g., "1.0")
6. Click **Upload Template**
7. Template is processed asynchronously by Cloud Function
8. Receive email notification when processing is complete

## Configuration

### Environment Variables

Add these to your backend configuration:

```bash
# Email Notifications
SENDGRID_API_KEY=SG.your-sendgrid-api-key
FROM_EMAIL=noreply@yourdomain.com

# Cloud Function
PROJECT_ID=btoproject-486405
REGION=us-central1
VERTEX_INDEX_ID=5347067982386298880
VERTEX_INDEX_ENDPOINT=332186652006940672
DEPLOYED_INDEX_ID=rag_chatbot_deployed
```

### GCP Services Required

```bash
# Enable required APIs
gcloud services enable \
  cloudfunctions.googleapis.com \
  pubsub.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com

# Create Pub/Sub topic
gcloud pubsub topics create compliance-template-ingestion

# Create GCS bucket for templates
gsutil mb -l us-central1 gs://btoproject-486405-compliance-templates

# Create Firestore collections (auto-created on first use)
# - compliance_reports
# - compliance_templates
# - compliance_template_chunks
```

### Service Account Permissions

Backend service account needs:
- `roles/aiplatform.user` - Vertex AI access
- `roles/storage.objectAdmin` - GCS access
- `roles/datastore.user` - Firestore access
- `roles/pubsub.publisher` - Pub/Sub publish

Cloud Function service account needs:
- `roles/aiplatform.user` - Vertex AI access
- `roles/storage.objectViewer` - GCS read
- `roles/datastore.user` - Firestore access
- `roles/pubsub.subscriber` - Pub/Sub consume

## Dependencies Added

### Backend (`requirements.txt`)
```
sendgrid==6.11.0  # Email notifications
```

All other dependencies (LangGraph, LangChain, Vertex AI) were already present.

### Frontend
No new dependencies required. Uses existing Angular Material components.

## Testing

### Manual Testing

#### 1. Test Document Upload
```bash
curl -X POST "http://localhost:8000/compliance/documents/upload" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@sample-policy.pdf" \
  -F "template_type=ISO27001"
```

#### 2. Test Template Upload (Admin)
```bash
curl -X POST "http://localhost:8000/compliance/templates/upload" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN" \
  -F "file=@iso27001-template.pdf" \
  -F "template_type=ISO27001" \
  -F "version=1.0"
```

#### 3. Test Report Retrieval
```bash
curl -X GET "http://localhost:8000/compliance/reports/REPORT_ID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Integration Testing

Run the existing test suite (covers core RAG components):
```bash
pytest tests/unit/ -v
```

For compliance-specific testing:
```bash
pytest tests/unit/test_compliance*.py -v
```

## Deployment

### 1. Deploy Cloud Function
```bash
cd cloud-functions/template-processor
gcloud functions deploy compliance-template-processor \
  --gen2 \
  --region=us-central1 \
  --runtime=python311 \
  --source=. \
  --entry-point=process_template \
  --trigger-topic=compliance-template-ingestion \
  --set-env-vars PROJECT_ID=btoproject-486405,REGION=us-central1 \
  --service-account=template-processor-sa@btoproject-486405.iam.gserviceaccount.com \
  --memory=1Gi \
  --timeout=540s
```

### 2. Deploy Backend (GKE)
```bash
# Build and push Docker image
docker build -t gcr.io/btoproject-486405/rag-backend:week3 .
docker push gcr.io/btoproject-486405/rag-backend:week3

# Update GKE deployment
kubectl set image deployment/rag-backend \
  backend=gcr.io/btoproject-486405/rag-backend:week3

# Verify rollout
kubectl rollout status deployment/rag-backend
```

### 3. Deploy Frontend
```bash
cd frontend
ng build --prod
docker build -t gcr.io/btoproject-486405/rag-frontend:week3 .
docker push gcr.io/btoproject-486405/rag-frontend:week3

kubectl set image deployment/rag-frontend \
  frontend=gcr.io/btoproject-486405/rag-frontend:week3
```

## Monitoring & Logging

### View Cloud Function Logs
```bash
gcloud functions logs read compliance-template-processor --limit=50
```

### View Backend Logs (GKE)
```bash
kubectl logs -f deployment/rag-backend
```

### Monitor Pub/Sub
```bash
# View topic details
gcloud pubsub topics describe compliance-template-ingestion

# View subscription details
gcloud pubsub subscriptions describe compliance-template-processing
```

### Check Firestore Collections
```bash
# Via Cloud Console
https://console.cloud.google.com/firestore/data

# Collections to check:
# - compliance_reports
# - compliance_templates
# - compliance_template_chunks
```

## Troubleshooting

### Issue: Template processing not starting
**Solution**: Check Pub/Sub topic and subscription:
```bash
gcloud pubsub topics list
gcloud pubsub subscriptions list
```

### Issue: Email notifications not sending
**Solution**: 
1. Verify `SENDGRID_API_KEY` is set
2. Check SendGrid dashboard for API key status
3. Review backend logs for email service errors

### Issue: Reports stuck in "processing" status
**Solution**:
1. Check backend logs for errors during workflow execution
2. Verify Vertex AI Vector Search is accessible
3. Check Firestore for error messages in report document
4. Re-run workflow manually:
   ```python
   from app.compliance.agents import ComplianceAgent
   # Initialize and run...
   ```

### Issue: Low compliance scores for valid documents
**Solution**:
1. Adjust similarity threshold in `TemplateMatcher` (default: 0.75)
2. Upload more specific templates for your document type
3. Check template chunking - may need adjustment for your use case

## Future Enhancements

Potential improvements for Week 4+:

1. **Advanced Template Matching**
   - Use graph-based matching for complex requirements
   - Add support for hierarchical requirements
   - Implement requirement dependency tracking

2. **Multi-Language Support**
   - Support documents in multiple languages
   - Translate requirements for cross-language compliance

3. **Automated Remediation**
   - Generate document patches to address gaps
   - Suggest specific text additions

4. **Compliance Tracking**
   - Track compliance over time (trending)
   - Compare different document versions
   - Alert on compliance degradation

5. **Advanced Reporting**
   - Export to PDF with formatting
   - Generate executive presentations
   - Create compliance certificates

6. **Template Management UI**
   - Browse and search templates
   - View template details and requirements
   - Template versioning and comparison

## Support

For issues or questions:
- Check logs: `kubectl logs -f deployment/rag-backend`
- Review documentation: [`docs/`](docs/)
- Contact: your-team@example.com

## License

Internal use only - Capgemini BTO Project
