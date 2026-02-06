"""
Enhanced FastAPI main application with Authentication, RBAC, Chat History, and Analytics.
"""

import os
import time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
from pydantic import BaseModel

from app.config import config
from app.logging_config import get_logger
from app.middleware import (
    RateLimitMiddleware, 
    ErrorHandlingMiddleware, 
    RequestValidationMiddleware,
    SecurityHeadersMiddleware
)

# Import authentication and authorization
from app.auth.oidc import get_current_user, get_optional_user
from app.auth.rbac import (
    get_current_user_with_role,
    require_permission,
    require_role,
    Permission,
    Role,
    rbac_manager
)

# Import existing RAG components
from app.rag.schemas import QueryRequest, QueryResponse, IngestResponse
from app.rag.chunker import extract_and_chunk
from app.rag.embeddings import VertexTextEmbedder
from app.rag.vector_store import VertexVectorStore
from app.rag.generator import GeminiGenerator
from app.rag.reranker import HybridReranker
from app.rag.ragas_eval import RAGASEvaluator
from app.rag.graph_rag import LangGraphRAGPipeline
from app.rag.pii_detector import PIIDetector
from app.storage.firestore_store import FirestoreChunkStore
from app.storage.gcs_store import GCSDocumentStore
from app.storage.redis_store import RedisChatHistory
from app.analytics import AnalyticsTracker
from app.telemetry import configure_otel, trace_operation, record_tokens, record_llm_generation

logger = get_logger(__name__)

# Service instances
embedder: Optional[VertexTextEmbedder] = None
vector_store: Optional[VertexVectorStore] = None
chunk_store: Optional[FirestoreChunkStore] = None
doc_store: Optional[GCSDocumentStore] = None
generator: Optional[GeminiGenerator] = None
reranker: Optional[HybridReranker] = None
evaluator: Optional[RAGASEvaluator] = None
pii_detector: Optional[PIIDetector] = None
langgraph_pipeline: Optional[LangGraphRAGPipeline] = None
redis_history: Optional[RedisChatHistory] = None
analytics: Optional[AnalyticsTracker] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    logger.info("Starting Enhanced RAG Service", config=config.to_dict())
    
    # Validate configuration
    validation = config.validate()
    if not validation["valid"]:
        logger.error("Configuration validation failed", issues=validation["issues"])
        raise RuntimeError(f"Invalid configuration: {validation['issues']}")
    
    # Initialize services
    global embedder, vector_store, chunk_store, doc_store, generator, reranker
    global evaluator, pii_detector, langgraph_pipeline, redis_history, analytics
    
    try:
        logger.info("Initializing services")
        
        # Existing services
        embedder = VertexTextEmbedder(
            project=config.PROJECT_ID, 
            location=config.VERTEX_LOCATION
        )
        
        vector_store = VertexVectorStore(
            project=config.PROJECT_ID,
            location=config.VERTEX_LOCATION,
            index_id=config.VERTEX_INDEX_ID,
            index_endpoint_name=config.VERTEX_INDEX_ENDPOINT,
            deployed_index_id=config.DEPLOYED_INDEX_ID
        )
        
        if config.USE_FIRESTORE:
            chunk_store = FirestoreChunkStore(
                project_id=config.PROJECT_ID,
                collection_name=config.FIRESTORE_COLLECTION
            )
        
        doc_store = GCSDocumentStore(
            project_id=config.PROJECT_ID,
            bucket_name=config.GCS_BUCKET
        )
        
        generator = GeminiGenerator(
            project=config.PROJECT_ID,
            location=config.VERTEX_LOCATION,
            model=config.MODEL_VARIANT
        )
        
        reranker = HybridReranker(
            project=config.PROJECT_ID,
            location=config.VERTEX_LOCATION
        )
        
        evaluator = RAGASEvaluator(
            project=config.PROJECT_ID,
            location=config.VERTEX_LOCATION,
            model=config.MODEL_VARIANT
        )
        
        pii_detector = PIIDetector(project_id=config.PROJECT_ID)
        
        langgraph_pipeline = LangGraphRAGPipeline(
            embeddings=embedder,
            vector_store=vector_store,
            reranker=reranker,
            generator=generator,
            max_iterations=2
        )
        
        # New services
        try:
            redis_history = RedisChatHistory(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD")
            )
            logger.info("Redis chat history initialized")
        except Exception as e:
            logger.warning("Redis not available, chat history disabled", error=str(e))
            redis_history = None
        
        analytics = AnalyticsTracker(
            project_id=config.PROJECT_ID,
            collection_name="analytics_metrics"
        )
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error("Service initialization failed", error=str(e))
        raise
    
    yield
    
    logger.info("Shutting down RAG service")


app = FastAPI(
    title="Production ChatBot RAG Service",
    version="3.0.0",
    description="Production-grade RAG system with Auth, RBAC, Chat History, and Analytics",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestValidationMiddleware, max_content_length=config.MAX_FILE_SIZE)
app.add_middleware(RateLimitMiddleware, max_requests=config.RATE_LIMIT_PER_MINUTE, window_seconds=60)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

configure_otel(app)


# ============================================================================
# PUBLIC ENDPOINTS
# ============================================================================

@app.get("/health")
def health():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "chatbot-rag-service",
        "version": "3.0.0"
    }


@app.get("/readiness")
async def readiness():
    """Readiness probe for Kubernetes."""
    checks = {
        "embedder": embedder is not None,
        "vector_store": vector_store is not None,
        "generator": generator is not None,
        "analytics": analytics is not None,
    }
    
    all_ready = all(checks.values())
    
    return {
        "ready": all_ready,
        "checks": checks,
        "timestamp": time.time()
    }


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

class LoginRequest(BaseModel):
    """Login request with Google ID token."""
    id_token: str


@app.post("/api/v1/auth/login")
async def login(request: LoginRequest):
    """
    Authenticate user with Google OIDC ID token.
    Returns user info and role.
    """
    from app.auth.oidc import get_oidc_validator
    
    validator = get_oidc_validator()
    user_info = validator.verify_token(request.id_token)
    
    # Get user role and permissions
    role = rbac_manager.get_user_role(user_info['email'])
    permissions = rbac_manager.get_user_permissions(user_info['email'])
    
    return {
        "user": user_info,
        "role": role.value,
        "permissions": [p.value for p in permissions],
        "authenticated": True
    }


@app.get("/api/v1/auth/me")
async def get_me(user: Dict[str, Any] = Depends(get_current_user_with_role)):
    """Get current user information."""
    return {
        "user": user,
        "authenticated": True
    }


# ============================================================================
# CHAT ENDPOINTS (Protected)
# ============================================================================

class ChatQueryRequest(BaseModel):
    """Chat query request."""
    query: str
    session_id: Optional[str] = None
    top_k: int = 5
    use_reranking: bool = True


class ChatSessionResponse(BaseModel):
    """Chat session response."""
    session_id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str


@app.post("/api/v1/chat/query")
async def chat_query(
    request: ChatQueryRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    _auth: None = Depends(require_permission(Permission.QUERY_RAG))
):
    """
    Execute a RAG query within a chat session.
    Creates new session if session_id not provided.
    """
    start_time = time.time()
    user_id = user['email']
    
    try:
        # Create or get session
        if request.session_id and redis_history:
            session_id = request.session_id
        elif redis_history:
            session_id = redis_history.create_session(user_id, request.query)
        else:
            session_id = "no-redis"
        
        # Add user message to history
        if redis_history:
            redis_history.add_message(session_id, 'user', request.query)
        
        # Get conversation context
        context_messages = []
        if redis_history and request.session_id:
            context_messages = redis_history.get_recent_context(session_id, max_messages=6)
        
        # Execute RAG query using LangGraph pipeline
        with trace_operation("rag_query"):
            result = langgraph_pipeline.query(
                query=request.query,
                top_k=request.top_k,
                use_reranking=request.use_reranking,
                context_history=context_messages
            )
        
        # Add assistant response to history
        if redis_history:
            redis_history.add_message(
                session_id,
                'assistant',
                result['answer'],
                metadata={
                    'tokens': result.get('metadata', {}).get('token_usage', {}),
                    'chunks_used': len(result.get('contexts', [])),
                    'latency_ms': result.get('metadata', {}).get('latency_ms', 0)
                }
            )
        
        # Track analytics
        response_time_ms = (time.time() - start_time) * 1000
        token_usage = result.get('metadata', {}).get('token_usage', {})
        
        if analytics:
            analytics.track_query(
                user_email=user_id,
                query=request.query,
                response_time_ms=response_time_ms,
                token_usage=token_usage,
                model=config.MODEL_VARIANT,
                success=True,
                metadata={
                    'session_id': session_id,
                    'chunks_retrieved': len(result.get('contexts', [])),
                    'reranking_used': request.use_reranking
                }
            )
        
        return {
            "answer": result['answer'],
            "session_id": session_id,
            "contexts": result.get('contexts', []),
            "metadata": {
                **result.get('metadata', {}),
                "response_time_ms": response_time_ms
            }
        }
        
    except Exception as e:
        logger.error("Chat query failed", error=str(e), user=user_id)
        
        # Track failure
        if analytics:
            analytics.track_query(
                user_email=user_id,
                query=request.query,
                response_time_ms=(time.time() - start_time) * 1000,
                token_usage={},
                model=config.MODEL_VARIANT,
                success=False,
                error=str(e)
            )
        
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/chat/sessions", response_model=List[ChatSessionResponse])
async def get_chat_sessions(
    user: Dict[str, Any] = Depends(get_current_user),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
):
    """Get all chat sessions for current user."""
    if not redis_history:
        raise HTTPException(status_code=503, detail="Chat history not available")
    
    user_id = user['email']
    sessions = redis_history.get_user_sessions(user_id, limit=limit, offset=offset)
    
    return sessions


@app.get("/api/v1/chat/sessions/{session_id}/history")
async def get_session_history(
    session_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get message history for a specific chat session."""
    if not redis_history:
        raise HTTPException(status_code=503, detail="Chat history not available")
    
    messages = redis_history.get_session_history(session_id)
    
    return {
        "session_id": session_id,
        "messages": messages
    }


@app.delete("/api/v1/chat/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    _auth: None = Depends(require_permission(Permission.DELETE_HISTORY))
):
    """Delete a chat session."""
    if not redis_history:
        raise HTTPException(status_code=503, detail="Chat history not available")
    
    user_id = user['email']
    redis_history.delete_session(session_id, user_id)
    
    return {"message": "Session deleted", "session_id": session_id}


# ============================================================================
# DOCUMENT MANAGEMENT ENDPOINTS (Protected)
# ============================================================================

@app.post("/api/v1/documents/ingest")
async def ingest_documents(
    files: List[UploadFile] = File(...),
    user: Dict[str, Any] = Depends(get_current_user),
    _auth: None = Depends(require_permission(Permission.UPLOAD_DOCUMENT))
):
    """Upload and process documents for RAG."""
    start_time = time.time()
    user_email = user['email']
    
    results = []
    
    for file in files:
        try:
            # Read file content
            content = await file.read()
            
            # Extract and chunk
            chunks = extract_and_chunk(
                content=content,
                filename=file.filename,
                chunking_strategy="semantic",
                max_chunk_size=512
            )
            
            # Generate embeddings
            chunk_texts = [c['text'] for c in chunks]
            embeddings = embedder.embed(chunk_texts)
            
            # Store in vector database
            chunk_ids = []
            for chunk, embedding in zip(chunks, embeddings):
                chunk_id = f"{file.filename}_{chunk['chunk_index']}"
                vector_store.upsert_vector(
                    vector_id=chunk_id,
                    embedding=embedding,
                    metadata=chunk
                )
                chunk_ids.append(chunk_id)
            
            # Store in GCS
            doc_uri = doc_store.upload_document(
                content=content,
                filename=file.filename,
                metadata={"uploaded_by": user_email}
            )
            
            # Track analytics
            processing_time_ms = (time.time() - start_time) * 1000
            if analytics:
                analytics.track_document_upload(
                    user_email=user_email,
                    filename=file.filename,
                    file_size_bytes=len(content),
                    chunks_created=len(chunks),
                    processing_time_ms=processing_time_ms,
                    success=True
                )
            
            results.append({
                "filename": file.filename,
                "chunks_created": len(chunks),
                "doc_uri": doc_uri,
                "status": "success"
            })
            
        except Exception as e:
            logger.error("Document ingestion failed", filename=file.filename, error=str(e))
            results.append({
                "filename": file.filename,
                "status": "failed",
                "error": str(e)
            })
    
    return {"results": results}


# ============================================================================
# ADMIN ANALYTICS ENDPOINTS (Admin Only)
# ============================================================================

@app.get("/api/v1/admin/analytics/usage")
async def get_usage_analytics(
    user: Dict[str, Any] = Depends(get_current_user),
    _auth: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
    days: int = Query(7, ge=1, le=90)
):
    """Get usage analytics (admin only)."""
    if not analytics:
        raise HTTPException(status_code=503, detail="Analytics not available")
    
    stats = analytics.get_usage_stats(days=days)
    return stats


@app.get("/api/v1/admin/analytics/users")
async def get_user_analytics(
    user: Dict[str, Any] = Depends(get_current_user),
    _auth: None = Depends(require_role(Role.ADMIN)),
    days: int = Query(30, ge=1, le=90)
):
    """Get per-user analytics (admin only)."""
    if not analytics:
        raise HTTPException(status_code=503, detail="Analytics not available")
    
    top_users = analytics.get_top_users(days=days, limit=20)
    return {"top_users": top_users}


@app.get("/api/v1/admin/analytics/models")
async def get_model_analytics(
    user: Dict[str, Any] = Depends(get_current_user),
    _auth: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
    days: int = Query(30, ge=1, le=90)
):
    """Get model usage analytics."""
    if not analytics:
        raise HTTPException(status_code=503, detail="Analytics not available")
    
    model_stats = analytics.get_model_usage(days=days)
    return {"models": model_stats}


@app.get("/api/v1/admin/analytics/hourly")
async def get_hourly_distribution(
    user: Dict[str, Any] = Depends(get_current_user),
    _auth: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
    days: int = Query(7, ge=1, le=30)
):
    """Get query distribution by hour."""
    if not analytics:
        raise HTTPException(status_code=503, detail="Analytics not available")
    
    distribution = analytics.get_hourly_distribution(days=days)
    return {"hourly_distribution": distribution}


# ============================================================================
# USER MANAGEMENT ENDPOINTS (Admin Only)
# ============================================================================

class AssignRoleRequest(BaseModel):
    """Request to assign role to user."""
    user_email: str
    role: str


@app.post("/api/v1/admin/users/assign-role")
async def assign_user_role(
    request: AssignRoleRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    _auth: None = Depends(require_permission(Permission.MANAGE_USERS))
):
    """Assign role to a user (admin only)."""
    try:
        role = Role(request.role)
        rbac_manager.assign_role(request.user_email, role)
        
        return {
            "message": "Role assigned successfully",
            "user_email": request.user_email,
            "role": role.value
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {request.role}")


@app.get("/api/v1/admin/users")
async def list_users(
    user: Dict[str, Any] = Depends(get_current_user),
    _auth: None = Depends(require_role(Role.ADMIN))
):
    """List all users and their roles."""
    users = rbac_manager.list_all_users()
    return {"users": users}


# ============================================================================
# USER PROFILE ENDPOINTS
# ============================================================================

@app.get("/api/v1/user/stats")
async def get_user_stats(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get statistics for current user."""
    user_email = user['email']
    
    stats = {}
    
    # Chat history stats
    if redis_history:
        stats['chat'] = redis_history.get_stats(user_email)
    
    # Usage stats
    if analytics:
        stats['usage'] = analytics.get_user_usage(user_email, days=30)
    
    return stats


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main_enhanced:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        reload=True
    )
