"""
Compliance API Routes for Document Compliance Checking.
New endpoints for Week 3 requirements - integrated with existing RAG system.
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks, status
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime
import json

from app.auth.oidc import get_current_user
from app.auth.rbac import Permission, get_rbac_manager
from app.logging_config import get_logger

logger = get_logger(__name__)

# Create router
compliance_router = APIRouter(prefix="/compliance", tags=["Compliance"])


# ==================== Pydantic Models ====================

class ComplianceReportRequest(BaseModel):
    """Request for compliance report generation."""
    document_id: str
    template_type: Optional[str] = Field(None, description="Template type filter (e.g., ISO27001, GDPR)")


class ComplianceReportResponse(BaseModel):
    """Response with compliance report details."""
    report_id: str
    document_id: str
    compliance_score: float
    report_url: str
    gaps_count: int
    status: str  # "processing", "completed", "failed"
    created_at: datetime


class ComplianceReportDetail(BaseModel):
    """Detailed compliance report."""
    report_id: str
    document_id: str
    user_id: str
    compliance_score: float
    report: str  # Markdown report
    recommendations: List[str]
    gaps: List[dict]
    matched_sections: List[dict]
    templates_used: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None


class TemplateUploadResponse(BaseModel):
    """Response for template upload."""
    template_id: str
    status: str  # "processing", "completed", "failed"
    message: str


class DocumentUploadRequest(BaseModel):
    """Request for document upload and compliance checking."""
    template_type: Optional[str] = None


# ==================== API Endpoints ====================

@compliance_router.post("/documents/upload", response_model=ComplianceReportResponse)
async def upload_document_for_compliance(
    file: UploadFile = File(..., description="Document file (PDF, DOCX, TXT)"),
    template_type: Optional[str] = Form(None, description="Template type to check against"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload document for compliance checking.
    
    Workflow:
    1. Upload document to GCS
    2. Chunk and embed document
    3. Trigger agentic compliance workflow (async)
    4. Return report_id for status polling
    
    Requires: DOCUMENT_UPLOAD permission
    """
    try:
        print(f"[DEBUG] Upload started, current_user type: {type(current_user)}, value: {current_user}")
        
        # Check permission
        rbac = get_rbac_manager()
        print(f"[DEBUG] Checking permissions for role: {current_user.get('role', 'guest')}")
        if not rbac.has_permission(current_user.get("role", "guest"), Permission.DOCUMENT_UPLOAD):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Import services (lazy import to avoid circular dependencies)
        print(f"[DEBUG] Starting imports")
        from app.storage.gcs_store import GCSDocumentStore
        print(f"[DEBUG] Imported GCSDocumentStore")
        from app.storage.firestore_store import FirestoreChunkStore
        print(f"[DEBUG] Imported FirestoreChunkStore")
        from app.rag.chunker import extract_and_chunk
        print(f"[DEBUG] Imported extract_and_chunk")
        from app.config import config
        print(f"[DEBUG] All imports complete")
        
        # Generate unique IDs
        print(f"[DEBUG] Generating IDs")
        document_id = str(uuid.uuid4())
        report_id = str(uuid.uuid4())
        print(f"[DEBUG] IDs generated: doc={document_id[:8]}, report={report_id[:8]}")
        
        logger.info(f"Processing compliance upload: document_id={document_id}, user={current_user.get('user_id')}")
        
        # Read file content
        print(f"[DEBUG] Reading file: {file.filename}")
        content = await file.read()
        print(f"[DEBUG] File read complete, size: {len(content)} bytes")
        
        # Upload to GCS
        print(f"[DEBUG] Initializing GCS store")
        doc_store = GCSDocumentStore(
            project_id=config.PROJECT_ID,
            bucket_name=config.GCS_BUCKET
        )
        
        print(f"[DEBUG] Uploading to GCS: {file.filename}")
        gcs_uri = doc_store.upload_document(
            filename=file.filename,
            content=content,
            content_type=file.content_type,
            metadata={
                "document_id": document_id,
                "user_id": current_user.get("user_id"),
                "uploaded_at": datetime.utcnow().isoformat(),
                "purpose": "compliance_check"
            }
        )
        print(f"[DEBUG] GCS upload complete: {gcs_uri}")
        
        # Chunk document
        print(f"[DEBUG] Starting document chunking")
        chunks = extract_and_chunk([(file.filename, content)])
        print(f"[DEBUG] Chunking complete, chunks type: {type(chunks)}, count: {len(chunks)}")
        print(f"[DEBUG] First chunk type: {type(chunks[0]) if chunks else 'N/A'}")
        document_text = " ".join([chunk.get("text", "") for chunk in chunks])
        print(f"[DEBUG] Document text extracted, length: {len(document_text)}")
        
        # Store initial report metadata in Firestore
        print(f"[DEBUG] Initializing Firestore store")
        chunk_store = FirestoreChunkStore(
            project_id=config.PROJECT_ID,
            collection_name="compliance_reports"
        )
        
        print(f"[DEBUG] Storing report metadata in Firestore")
        chunk_store.store_chunk({
            "id": report_id,
            "report_id": report_id,
            "document_id": document_id,
            "user_id": current_user.get("user_id"),
            "user_email": current_user.get("email"),
            "gcs_uri": gcs_uri,
            "filename": file.filename,
            "template_type": template_type,
            "status": "processing",
            "created_at": datetime.utcnow().isoformat(),
            "chunks_count": len(chunks)
        })
        print(f"[DEBUG] Firestore metadata stored successfully")
        
        # Trigger compliance workflow (background task)
        print(f"[DEBUG] Adding background task for compliance workflow")
        background_tasks.add_task(
            run_compliance_workflow_background,
            report_id=report_id,
            document_id=document_id,
            document_text=document_text,
            template_type=template_type,
            user_email=current_user.get("email"),
            user_name=current_user.get("name")
        )
        
        logger.info(f"Compliance check initiated: report_id={report_id}")
        
        return ComplianceReportResponse(
            report_id=report_id,
            document_id=document_id,
            compliance_score=0.0,  # Not yet calculated
            report_url=f"/compliance/reports/{report_id}",
            gaps_count=0,
            status="processing",
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error uploading document for compliance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@compliance_router.get("/reports/{report_id}", response_model=ComplianceReportDetail)
async def get_compliance_report(
    report_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get compliance report by ID.
    
    Returns detailed compliance report with score, gaps, and recommendations.
    
    Requires: DOCUMENT_VIEW_OWN permission
    """
    try:
        # Import Firestore store
        from app.storage.firestore_store import FirestoreChunkStore
        from app.config import config
        
        # Check permission
        rbac = get_rbac_manager()
        if not rbac.has_permission(current_user.get("role", "guest"), Permission.DOCUMENT_VIEW_OWN):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Fetch from Firestore
        chunk_store = FirestoreChunkStore(
            project_id=config.PROJECT_ID,
            collection_name="compliance_reports"
        )
        
        report_data = chunk_store.get_chunk(report_id)
        
        if not report_data:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Check user has access (own report or admin)
        if report_data.get("user_id") != current_user.get("user_id") and current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Convert to response model
        return ComplianceReportDetail(
            report_id=report_data.get("report_id", report_id),
            document_id=report_data.get("document_id", ""),
            user_id=report_data.get("user_id", ""),
            compliance_score=report_data.get("compliance_score", 0.0),
            report=report_data.get("report", ""),
            recommendations=report_data.get("recommendations", []),
            gaps=report_data.get("gaps", []),
            matched_sections=report_data.get("matched_sections", []),
            templates_used=report_data.get("templates_used", 0),
            status=report_data.get("status", "unknown"),
            created_at=datetime.fromisoformat(report_data.get("created_at", datetime.utcnow().isoformat())),
            completed_at=datetime.fromisoformat(report_data["completed_at"]) if report_data.get("completed_at") else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching compliance report {report_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch report: {str(e)}")


@compliance_router.get("/reports", response_model=List[ComplianceReportResponse])
async def list_compliance_reports(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """
    List compliance reports for current user.
    
    Returns paginated list of compliance reports.
    
    Requires: DOCUMENT_VIEW_OWN permission
    """
    try:
        # Import Firestore store
        from app.storage.firestore_store import FirestoreChunkStore
        from app.config import config
        from google.cloud import firestore
        
        # Check permission
        rbac = get_rbac_manager()
        if not rbac.has_permission(current_user.get("role", "guest"), Permission.DOCUMENT_VIEW_OWN):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Query Firestore
        db = firestore.Client(project=config.PROJECT_ID)
        collection = db.collection("compliance_reports")
        
        # Filter by user (unless admin)
        if current_user.get("role") == "admin":
            query = collection.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit).offset(offset)
        else:
            query = collection.where("user_id", "==", current_user.get("user_id")).order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit).offset(offset)
        
        docs = query.stream()
        
        reports = []
        for doc in docs:
            data = doc.to_dict()
            reports.append(ComplianceReportResponse(
                report_id=data.get("report_id", doc.id),
                document_id=data.get("document_id", ""),
                compliance_score=data.get("compliance_score", 0.0),
                report_url=f"/compliance/reports/{doc.id}",
                gaps_count=len(data.get("gaps", [])),
                status=data.get("status", "unknown"),
                created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat()))
            ))
        
        logger.info(f"Listed {len(reports)} compliance reports for user {current_user.get('user_id')}")
        
        return reports
        
    except Exception as e:
        logger.error(f"Error listing compliance reports: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list reports: {str(e)}")


@compliance_router.post("/templates/upload", response_model=TemplateUploadResponse)
async def upload_compliance_template(
    file: UploadFile = File(..., description="Template file (PDF, DOCX, TXT)"),
    template_type: str = Form(..., description="Template type/category (e.g., ISO27001, GDPR)"),
    version: str = Form("1.0", description="Template version"),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload compliance template.
    
    Uploads template to GCS and triggers Pub/Sub event for async processing.
    Template will be chunked, embedded, and stored in Vertex AI Vector Search.
    
    Requires: ADMIN_MANAGE_SYSTEM permission
    """
    try:
        # Check admin permission
        rbac = get_rbac_manager()
        if not rbac.has_permission(current_user.get("role", "guest"), Permission.ADMIN_MANAGE_SYSTEM):
            raise HTTPException(status_code=403, detail="Admin permission required")
        
        # Import services
        from app.storage.gcs_store import GCSDocumentStore
        from app.config import config
        from google.cloud import pubsub_v1
        
        # Generate template ID
        template_id = str(uuid.uuid4())
        
        logger.info(f"Processing template upload: template_id={template_id}, type={template_type}, user={current_user.get('user_id')}")
        
        # Upload to GCS (templates bucket)
        content = await file.read()
        bucket_name = f"{config.PROJECT_ID}-compliance-templates"
        blob_name = f"templates/{template_type}/{template_id}/{file.filename}"
        
        doc_store = GCSDocumentStore(
            project_id=config.PROJECT_ID,
            bucket_name=bucket_name
        )
        
        gcs_uri = doc_store.upload_document(
            filename=blob_name,
            content=content,
            content_type=file.content_type,
            metadata={
                "template_id": template_id,
                "template_type": template_type,
                "version": version,
                "uploaded_by": current_user.get("user_id"),
                "uploaded_at": datetime.utcnow().isoformat()
            }
        )
        
        # Publish to Pub/Sub for async processing by Cloud Function
        try:
            publisher = pubsub_v1.PublisherClient()
            topic_path = f"projects/{config.PROJECT_ID}/topics/compliance-template-ingestion"
            
            message_data = {
                "template_id": template_id,
                "template_type": template_type,
                "version": version,
                "bucket": bucket_name,
                "blob_name": blob_name,
                "uploaded_by": current_user.get("user_id"),
                "user_email": current_user.get("email")
            }
            
            future = publisher.publish(
                topic_path,
                json.dumps(message_data).encode('utf-8')
            )
            future.result()  # Wait for publish confirmation
            
            logger.info(f"Template upload published to Pub/Sub: template_id={template_id}")
            
            return TemplateUploadResponse(
                template_id=template_id,
                status="processing",
                message=f"Template uploaded successfully. Processing in progress via Cloud Function."
            )
            
        except Exception as pubsub_error:
            logger.warning(f"Pub/Sub publish failed, falling back to direct processing: {pubsub_error}")
            
            # Fallback: Process inline if Pub/Sub not available
            from app.rag.chunker import extract_and_chunk
            from app.rag.embeddings import VertexTextEmbedder
            from app.rag.vector_store import VertexVectorStore
            from app.storage.firestore_store import FirestoreChunkStore
            
            # Chunk template
            chunks = extract_and_chunk(content, file.filename)
            
            # Embed chunks
            embedder = VertexTextEmbedder(project=config.PROJECT_ID, location=config.VERTEX_LOCATION)
            texts = [chunk.get("text", "") for chunk in chunks]
            embeddings = embedder.embed(texts)
            
            # Store in vector store (using existing index as fallback)
            vector_store = VertexVectorStore(
                project=config.PROJECT_ID,
                location=config.VERTEX_LOCATION,
                index_id=config.VERTEX_INDEX_ID,
                index_endpoint_name=config.VERTEX_INDEX_ENDPOINT,
                deployed_index_id=config.DEPLOYED_INDEX_ID
            )
            
            # Add template metadata
            for chunk in chunks:
                if "metadata" not in chunk:
                    chunk["metadata"] = {}
                chunk["metadata"]["template_id"] = template_id
                chunk["metadata"]["template_type"] = template_type
                chunk["metadata"]["version"] = version
                chunk["metadata"]["is_template"] = True
            
            vector_store.upsert(chunks, embeddings)
            
            # Store metadata in Firestore
            chunk_store = FirestoreChunkStore(
                project_id=config.PROJECT_ID,
                collection_name="compliance_templates"
            )
            
            chunk_store.store_chunk({
                "id": template_id,
                "template_id": template_id,
                "template_type": template_type,
                "version": version,
                "gcs_uri": gcs_uri,
                "chunk_count": len(chunks),
                "uploaded_by": current_user.get("user_id"),
                "status": "ready",
                "created_at": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Template processed inline: template_id={template_id}, chunks={len(chunks)}")
            
            return TemplateUploadResponse(
                template_id=template_id,
                status="completed",
                message=f"Template processed successfully: {len(chunks)} chunks created."
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Template upload failed: {str(e)}")


@compliance_router.delete("/reports/{report_id}")
async def delete_compliance_report(
    report_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete compliance report.
    
    Requires: DOCUMENT_DELETE_OWN permission or admin role
    """
    try:
        # Import Firestore
        from app.config import config
        from google.cloud import firestore
        
        # Check permission
        rbac = get_rbac_manager()
        if not rbac.has_permission(current_user.get("role", "guest"), Permission.DOCUMENT_DELETE_OWN):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Get report to check ownership
        db = firestore.Client(project=config.PROJECT_ID)
        doc_ref = db.collection("compliance_reports").document(report_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Report not found")
        
        report_data = doc.to_dict()
        
        # Check ownership (unless admin)
        if report_data.get("user_id") != current_user.get("user_id") and current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete report
        doc_ref.delete()
        
        logger.info(f"Deleted compliance report: report_id={report_id}, user={current_user.get('user_id')}")
        
        return {"message": "Report deleted successfully", "report_id": report_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting report {report_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete report: {str(e)}")


# ==================== Background Task ====================

async def run_compliance_workflow_background(
    report_id: str,
    document_id: str,
    document_text: str,
    template_type: Optional[str],
    user_email: Optional[str],
    user_name: Optional[str]
):
    """
    Background task to run compliance workflow.
    
    Args:
        report_id: Report identifier
        document_id: Document identifier
        document_text: Full document text
        template_type: Template type filter
        user_email: User's email for notification
        user_name: User's name for notification
    """
    try:
        logger.info(f"Starting compliance workflow background task: report_id={report_id}")
        
        # Import services
        from app.compliance.agents import ComplianceAgent
        from app.rag.embeddings import VertexTextEmbedder
        from app.rag.vector_store import VertexVectorStore
        from app.rag.generator import GeminiGenerator
        from app.storage.firestore_store import FirestoreChunkStore
        from app.notifications.email_service import EmailService
        from app.config import config
        
        # Initialize agent
        embedder = VertexTextEmbedder(project=config.PROJECT_ID, location=config.VERTEX_LOCATION)
        template_vector_store = VertexVectorStore(
            project=config.PROJECT_ID,
            location=config.VERTEX_LOCATION,
            index_id=config.VERTEX_INDEX_ID,
            index_endpoint_name=config.VERTEX_INDEX_ENDPOINT,
            deployed_index_id=config.DEPLOYED_INDEX_ID
        )
        document_vector_store = template_vector_store  # Using same index
        generator = GeminiGenerator(
            project=config.PROJECT_ID,
            location=config.VERTEX_LOCATION,
            model_name=config.MODEL_VARIANT
        )
        
        agent = ComplianceAgent(
            embeddings=embedder,
            template_vector_store=template_vector_store,
            document_vector_store=document_vector_store,
            generator=generator,
            max_iterations=2
        )
        
        # Run compliance workflow
        result = agent.run_sync(
            document_id=document_id,
            document_text=document_text,
            template_type=template_type
        )
        
        # Update Firestore with results
        chunk_store = FirestoreChunkStore(
            project_id=config.PROJECT_ID,
            collection_name="compliance_reports"
        )
        
        chunk_store.update_chunk(report_id, {
            "compliance_score": result.get("compliance_score", 0.0),
            "report": result.get("report", ""),
            "recommendations": result.get("recommendations", []),
            "gaps": result.get("gaps", []),
            "matched_sections": result.get("matched_sections", []),
            "templates_used": result.get("templates_used", 0),
            "gaps_count": len(result.get("gaps", [])),
            "status": result.get("status", "completed"),
            "completed_at": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Compliance workflow completed: report_id={report_id}, score={result.get('compliance_score', 0):.1f}%")
        
        # Send email notification
        if user_email:
            try:
                email_service = EmailService()
                email_service.send_compliance_report_ready(
                    to_email=user_email,
                    user_name=user_name,
                    report_id=report_id,
                    document_id=document_id,
                    compliance_score=result.get("compliance_score", 0.0),
                    report_url=f"https://your-app-url.com/compliance/reports/{report_id}",
                    gaps_count=len(result.get("gaps", []))
                )
            except Exception as email_error:
                logger.warning(f"Failed to send email notification: {email_error}")
        
    except Exception as e:
        logger.error(f"Error in compliance workflow background task: {e}", exc_info=True)
        
        # Update Firestore with error
        try:
            from app.storage.firestore_store import FirestoreChunkStore
            from app.config import config
            
            chunk_store = FirestoreChunkStore(
                project_id=config.PROJECT_ID,
                collection_name="compliance_reports"
            )
            chunk_store.update_chunk(report_id, {
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.utcnow().isoformat()
            })
        except:
            pass

