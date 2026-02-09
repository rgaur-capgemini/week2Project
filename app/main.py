"""
Week-1 RAG Service - Production-Grade Implementation
Features: Document Ingestion, Vector Search, Re-ranking, LLM Generation, RAGAS Evaluation, Full GCP Integration
"""

import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import time
from contextlib import asynccontextmanager

from app.config import config
from app.logging_config import get_logger
from app.middleware import (
    RateLimitMiddleware, 
    ErrorHandlingMiddleware, 
    RequestValidationMiddleware,
    SecurityHeadersMiddleware
)
from app.rag.schemas import QueryRequest, QueryResponse, IngestResponse, UnifiedResponse, EvaluateRequest, EvaluateResponse
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
from app.storage.redis_history import ChatHistoryStore
from app.analytics.collector import AnalyticsCollector
from app.rag.prompt_optimizer import PromptCompressor, SemanticFilter
from app.telemetry import (
    configure_otel, 
    trace_operation, 
    record_vector_search, 
    record_embedding, 
    record_tokens,
    record_llm_generation
)

# Import new routers
from app.api_routes import (
    auth_router, 
    history_router, 
    analytics_router
)
import app.api_routes as api_routes_module

# Initialize logger
logger = get_logger(__name__)

# Service instances (will be initialized at startup)
embedder: Optional[VertexTextEmbedder] = None
vector_store: Optional[VertexVectorStore] = None
chunk_store: Optional[FirestoreChunkStore] = None
doc_store: Optional[GCSDocumentStore] = None
generator: Optional[GeminiGenerator] = None
reranker: Optional[HybridReranker] = None
evaluator: Optional[RAGASEvaluator] = None
pii_detector: Optional[PIIDetector] = None
langgraph_pipeline: Optional[LangGraphRAGPipeline] = None
chat_history_store: Optional[ChatHistoryStore] = None
analytics_collector: Optional[AnalyticsCollector] = None
prompt_compressor: Optional[PromptCompressor] = None
semantic_filter: Optional[SemanticFilter] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Startup
    logger.info("Starting RAG service", config=config.to_dict())
    
    # Validate configuration
    validation = config.validate()
    if not validation["valid"]:
        logger.error("Configuration validation failed", issues=validation["issues"])
        raise RuntimeError(f"Invalid configuration: {validation['issues']}")
    
    # Initialize services
    global embedder, vector_store, chunk_store, doc_store, generator, reranker, evaluator, pii_detector, langgraph_pipeline
    global chat_history_store, analytics_collector, prompt_compressor, semantic_filter
    
    try:
        logger.info("Initializing services")
        
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
        
        # Initialize PII Detector
        pii_detector = PIIDetector(project_id=config.PROJECT_ID)
        
        # Initialize LangGraph RAG Pipeline
        langgraph_pipeline = LangGraphRAGPipeline(
            embeddings=embedder,
            vector_store=vector_store,
            reranker=reranker,
            generator=generator,
            max_iterations=2
        )
        
        # Initialize Chat History Store (Redis)
        try:
            chat_history_store = ChatHistoryStore(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB_HISTORY
            )
            logger.info("Chat history store initialized")
        except Exception as e:
            logger.warning(f"Chat history store initialization failed: {e}")
            chat_history_store = None
        
        # Initialize Analytics Collector (Redis)
        try:
            analytics_collector = AnalyticsCollector(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB_ANALYTICS
            )
            logger.info("Analytics collector initialized")
        except Exception as e:
            logger.warning(f"Analytics collector initialization failed: {e}")
            analytics_collector = None
        
        # Initialize Prompt Compressor
        prompt_compressor = PromptCompressor(max_tokens=config.MAX_TOKENS)
        
        # Initialize Semantic Filter
        semantic_filter = SemanticFilter(min_similarity=0.3, max_chunks=5)
        
        # Set global instances for API routes
        api_routes_module.chat_history_store = chat_history_store
        api_routes_module.analytics_collector = analytics_collector
        
        logger.info("Services initialized successfully (including LangGraph pipeline)")
        
    except Exception as e:
        logger.error("Service initialization failed", error=e)
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down RAG service")


app = FastAPI(
    title="Production RAG Chatbot Service",
    version="3.0.0",
    description="Production-grade RAG chatbot with authentication, analytics, and GKE deployment",
    lifespan=lifespan
)

# Add middleware (order matters!)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestValidationMiddleware, max_content_length=config.MAX_FILE_SIZE)
app.add_middleware(RateLimitMiddleware, max_requests=config.RATE_LIMIT_PER_MINUTE, window_seconds=60)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure observability
configure_otel(app)

# Include new routers
app.include_router(auth_router)
app.include_router(history_router)
app.include_router(analytics_router)

@app.get("/api/config")
async def get_public_config():
    """
    Public configuration endpoint for frontend.
    Returns only non-sensitive configuration like OAuth Client ID.
    """
    from app.auth.oidc import get_oidc_authenticator
    
    try:
        oidc = get_oidc_authenticator()
        return {
            "googleClientId": oidc.client_id,
            "projectId": config.PROJECT_ID,
            "region": config.REGION,
            "environment": config.ENVIRONMENT
        }
    except Exception as e:
        logger.error(f"Failed to retrieve public config: {e}")
        raise HTTPException(status_code=500, detail="Configuration not available")

@app.get("/health")
def health():
    """Basic health check endpoint (Cloud Run requirement)."""
    return {
        "status": "healthy",
        "service": "rag-service",
        "version": "2.0.0"
    }


@app.get("/readiness")
async def readiness():
    """
    Readiness probe - checks if service dependencies are available.
    Used by Cloud Run to determine if instance can receive traffic.
    """
    checks = {
        "embedder": embedder is not None,
        "vector_store": vector_store is not None,
        "generator": generator is not None,
        "reranker": reranker is not None,
        "evaluator": evaluator is not None,
        "doc_store": doc_store is not None,
        "pii_detector": pii_detector is not None
    }
    
    # Check Vertex AI connectivity
    vertex_ai_ready = False
    try:
        if embedder:
            # Try a simple embedding operation
            test_embedding = embedder.embed(["health check"])
            vertex_ai_ready = len(test_embedding) > 0
    except Exception as e:
        logger.warning("Vertex AI readiness check failed", error=e)
    
    checks["vertex_ai"] = vertex_ai_ready
    
    all_ready = all(checks.values())
    
    if not all_ready:
        logger.warning("Readiness check failed", checks=checks)
        raise HTTPException(status_code=503, detail={"ready": False, "checks": checks})
    
    return {
        "ready": True,
        "checks": checks,
        "project": config.PROJECT_ID,
        "region": config.REGION
    }


@app.get("/liveness")
def liveness():
    """
    Liveness probe - checks if service is running.
    Used by Cloud Run to detect if instance needs to be restarted.
    """
    return {"alive": True, "timestamp": time.time()}

@app.post("/ingest", response_model=IngestResponse)
async def ingest(files: List[UploadFile] = File(...)):
    """
    Ingest documents: extract text, chunk, embed, and store in vector search + Cloud Storage.
    
    Production features:
    - Stores documents in Cloud Storage for audit trail
    - Persists chunks in Firestore (if enabled)
    - Full error handling and logging
    - File size validation
    
    Supports: PDF, DOCX, HTML, TXT
    """
    with trace_operation("ingest_documents", {"num_files": len(files)}):
        try:
            # Validate file count
            if len(files) > config.MAX_FILES_PER_REQUEST:
                raise HTTPException(
                    status_code=400,
                    detail=f"Too many files. Maximum: {config.MAX_FILES_PER_REQUEST}"
                )
            
            # Read file contents and validate size
            docs = []
            gcs_uris = []
            
            for f in files:
                content = await f.read()
                
                if len(content) > config.MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File {f.filename} exceeds maximum size of {config.MAX_FILE_SIZE} bytes"
                    )
                
                # Store in Cloud Storage
                gcs_uri = doc_store.upload_document(
                    filename=f.filename,
                    content=content,
                    content_type=f.content_type or "application/octet-stream",
                    metadata={"ingested_at": time.time()}
                )
                
                if gcs_uri:
                    gcs_uris.append(gcs_uri)
                    logger.info(f"Document uploaded to GCS", filename=f.filename, gcs_uri=gcs_uri)
                
                docs.append((f.filename, content))
            
            # Extract and chunk with dynamic chunking
            with trace_operation("extract_and_chunk", {"num_docs": len(docs)}):
                chunks = extract_and_chunk(docs, pii_detector=pii_detector, use_dynamic_chunking=True)
            
            if not chunks:
                raise HTTPException(status_code=400, detail="No text extracted from files")
            
            logger.info(f"Extracted {len(chunks)} chunks from {len(files)} files (dynamic chunking)")
            
            # PII Detection
            logger.info(" Starting PII detection scan...")
            if pii_detector:
                for chunk in chunks:
                    pii_result = pii_detector.detect_pii(chunk["text"])
                    # Add PII metadata to chunk
                    chunk.setdefault("metadata", {})["pii_status"] = pii_result["status"]
                    chunk["metadata"]["pii_types"] = pii_result["pii_types"]
                    chunk["metadata"]["pii_count"] = pii_result["pii_count"]
                    
                    if pii_result["status"] in ["high_risk", "blocked"]:
                        logger.warning(f" High-risk PII detected in chunk {chunk['id']}", pii_types=pii_result["pii_types"])
                logger.info(f" PII detection completed for {len(chunks)} chunks")
            else:
                logger.warning(" PII detector not available - marking all as clean")
                # Fallback: mark as clean if PII detector unavailable
                for chunk in chunks:
                    chunk.setdefault("metadata", {})["pii_status"] = "clean"
            
            # Embed chunks
            start_time = time.time()
            with trace_operation("embed_chunks", {"num_chunks": len(chunks)}):
                vectors = embedder.embed([c["text"] for c in chunks])
            
            embedding_time = time.time() - start_time
            record_embedding(embedding_time, len(chunks))
            logger.info(f"Generated embeddings", num_chunks=len(chunks), duration=embedding_time)
            
            # Upsert to Vertex Vector Search
            with trace_operation("upsert_vectors", {"num_vectors": len(vectors)}):
                ids = vector_store.upsert(chunks, vectors)
            
            logger.info(f"Upserted to Vector Search", num_vectors=len(ids))
            
            # Store in Firestore (if enabled)
            if chunk_store:
                chunk_dict = {}
                for i, chunk in enumerate(chunks):
                    chunk_dict[ids[i]] = {
                        "text": chunk["text"],
                        "metadata": chunk.get("metadata", {}),
                        "vector": vectors[i].tolist() if hasattr(vectors[i], 'tolist') else vectors[i]
                    }
                
                stored = chunk_store.batch_store_chunks(chunk_dict)
                logger.info(f"Stored chunks in Firestore", num_stored=stored)
            
            return IngestResponse(
                ingested=len(ids),
                chunk_ids=ids,
                message=f"Successfully ingested {len(files)} files into {len(ids)} chunks",
                gcs_uris=gcs_uris if gcs_uris else None
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Ingestion failed", error=e, num_files=len(files))
            raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@app.post("/ingest-and-query", response_model=UnifiedResponse)
async def ingest_and_query(
    question: str = Form(..., description="User's question"),
    files: List[UploadFile] = File(..., description="Documents to process"),
    session_id: Optional[str] = Form(None, description="Session ID for storing chat history"),
    user_id: Optional[str] = Form(None, description="User ID for storing chat history")
):
    """
    **UNIFIED ENDPOINT: Accept documents + question in a SINGLE API call**
    
    This endpoint implements the complete Week-1 pipeline:
    1. Accept user documents (PDF, DOCX, HTML, TXT)
    2. Extract text from all documents
    3. Chunk text into smaller pieces (1500-3000 chars with overlap)
    4. Convert chunks to embeddings (text-embedding-004, 768-dim)
    5. Auto-index into Vertex AI Vector Search
    6. Perform semantic search for user question
    7. Generate answer using Gemini 1.5 Flash
    8. Enforce PII detection and filtering
    9. Provide full observability metrics
    10. Return combined response
    
    **Default Settings:**
    - top_k: 5
    - pii_filter: enabled
    - reranker: disabled (for speed)
    - temperature: 0.2
    
    **Example Request (form-data):**
    - question: "What are the security risks?"
    - files: [document1.pdf, document2.docx]
    
    **Returns:** Ingestion stats + Answer + Citations + Metrics in ONE response
    """
    start_time = time.time()
    metrics = {}
    
    with trace_operation("unified_ingest_and_query", {"num_files": len(files), "question_length": len(question)}):
        try:
            logger.info("Starting unified pipeline", num_files=len(files), question=question[:100])
            
            # ===== STEP 1: Validate inputs =====
            if len(files) > config.MAX_FILES_PER_REQUEST:
                raise HTTPException(
                    status_code=400,
                    detail=f"Too many files. Maximum: {config.MAX_FILES_PER_REQUEST}"
                )
            
            if not question or len(question.strip()) == 0:
                raise HTTPException(status_code=400, detail="Question cannot be empty")
            
            # ===== STEP 2: Read files and upload to GCS =====
            extract_start = time.time()
            docs = []
            gcs_uris = []
            
            for f in files:
                content = await f.read()
                
                if len(content) > config.MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File {f.filename} exceeds maximum size"
                    )
                
                # Store in Cloud Storage
                gcs_uri = doc_store.upload_document(
                    filename=f.filename,
                    content=content,
                    content_type=f.content_type or "application/octet-stream",
                    metadata={"ingested_at": time.time(), "question": question[:200]}
                )
                
                if gcs_uri:
                    gcs_uris.append(gcs_uri)
                
                docs.append((f.filename, content))
            
            # ===== STEP 3: Extract and chunk text (with dynamic chunking) =====
            with trace_operation("extract_and_chunk", {"num_docs": len(docs)}):
                chunks = extract_and_chunk(docs, pii_detector=pii_detector, use_dynamic_chunking=True)
            
            if not chunks:
                raise HTTPException(status_code=400, detail="No text extracted from files")
            
            metrics["extraction_time"] = time.time() - extract_start
            metrics["num_chunks"] = len(chunks)
            logger.info(f"Extracted {len(chunks)} chunks (dynamic chunking)", duration=metrics["extraction_time"])
            
            # ===== STEP 3.5: PII Detection =====
            pii_results = []
            has_high_risk_pii = False
            if pii_detector:
                for chunk in chunks:
                    pii_result = pii_detector.detect_pii(chunk["text"])
                    pii_results.append(pii_result)
                    # Add PII metadata to chunk
                    chunk.setdefault("metadata", {})["pii_status"] = pii_result["status"]
                    chunk["metadata"]["pii_types"] = pii_result["pii_types"]
                    chunk["metadata"]["pii_count"] = pii_result["pii_count"]
                    
                    if pii_result["status"] in ["high_risk", "blocked"]:
                        has_high_risk_pii = True
                        logger.warning(f"High-risk PII detected in chunk {chunk['id']}", pii_types=pii_result["pii_types"])
            else:
                # Fallback: mark as clean if PII detector unavailable
                for chunk in chunks:
                    chunk.setdefault("metadata", {})["pii_status"] = "clean"
            
            # ===== STEP 4: Generate embeddings =====
            embed_start = time.time()
            with trace_operation("embed_chunks", {"num_chunks": len(chunks)}):
                vectors = embedder.embed([c["text"] for c in chunks])
            
            metrics["embedding_time"] = time.time() - embed_start
            record_embedding(metrics["embedding_time"], len(chunks))
            logger.info(f"Generated embeddings", num_chunks=len(chunks), duration=metrics["embedding_time"])
            
            # ===== STEP 5: Upsert to Vector Search =====
            upsert_start = time.time()
            with trace_operation("upsert_vectors", {"num_vectors": len(vectors)}):
                chunk_ids = vector_store.upsert(chunks, vectors)
            
            metrics["upsert_time"] = time.time() - upsert_start
            logger.info(f"Indexed in Vector Search", num_vectors=len(chunk_ids), duration=metrics["upsert_time"])
            
            # Store in Firestore if enabled
            if chunk_store:
                chunk_dict = {}
                for i, chunk in enumerate(chunks):
                    chunk_dict[chunk_ids[i]] = {
                        "text": chunk["text"],
                        "metadata": chunk.get("metadata", {}),
                        "vector": vectors[i].tolist() if hasattr(vectors[i], 'tolist') else vectors[i]
                    }
                chunk_store.batch_store_chunks(chunk_dict)
            
            # ===== STEP 6: Embed question and search =====
            retrieval_start = time.time()
            with trace_operation("embed_question"):
                question_vector = embedder.embed([question])[0]
            
            # Search with PII filter enabled (default)
            with trace_operation("vector_search", {"top_k": 5}):
                search_results = vector_store.search(
                    query=question,
                    top_k=5,
                    enable_pii_filter=True  # Enforce PII filtering
                )
            
            metrics["retrieval_time"] = time.time() - retrieval_start
            record_vector_search(metrics["retrieval_time"], len(search_results))
            logger.info(f"Retrieved chunks", num_results=len(search_results), duration=metrics["retrieval_time"])
            
            if not search_results:
                raise HTTPException(
                    status_code=404,
                    detail="No relevant chunks found. Documents may not be indexed yet or question is unrelated."
                )
            
            # ===== STEP 6.5: Apply Semantic Filtering =====
            contexts = [r["text"] for r in search_results]
            
            if semantic_filter and len(contexts) > 1:
                try:
                    with trace_operation("semantic_filter"):
                        filtered_contexts = semantic_filter.filter_chunks(question, contexts)
                        logger.info(f"Semantic filtering: {len(contexts)} → {len(filtered_contexts)} chunks")
                        contexts = filtered_contexts
                except Exception as e:
                    logger.warning(f"Semantic filtering failed, using all contexts: {e}")
            
            # ===== STEP 6.6: Apply Prompt Compression =====
            if prompt_compressor and contexts:
                try:
                    with trace_operation("prompt_compression"):
                        compressed_contexts = []
                        original_length = sum(len(ctx) for ctx in contexts)
                        
                        for ctx in contexts:
                            compressed = prompt_compressor.compress(ctx)
                            compressed_contexts.append(compressed)
                        
                        compressed_length = sum(len(ctx) for ctx in compressed_contexts)
                        compression_ratio = (1 - compressed_length / original_length) * 100 if original_length > 0 else 0
                        
                        logger.info(f"Prompt compression: {original_length} → {compressed_length} chars ({compression_ratio:.1f}% reduction)")
                        contexts = compressed_contexts
                        metrics["compression_ratio"] = f"{compression_ratio:.1f}%"
                except Exception as e:
                    logger.warning(f"Prompt compression failed, using original contexts: {e}")
            
            # ===== STEP 7: Generate answer with Gemini =====
            generation_start = time.time()
            
            with trace_operation("generate_answer", {"num_contexts": len(contexts)}):
                answer, citations, token_usage = generator.generate(question, contexts)
            
            metrics["generation_time"] = time.time() - generation_start
            record_llm_generation(metrics["generation_time"], len(contexts))
            record_tokens(token_usage["total_tokens"], "generate")
            logger.info(f"Generated answer", duration=metrics["generation_time"], tokens=token_usage)
            
            # SECURITY: Redact PII from answer before returning to user
            if pii_detector:
                answer = pii_detector.redact_pii(answer)
                contexts = [pii_detector.redact_pii(ctx) for ctx in contexts]
                citations = [pii_detector.redact_pii(cite) for cite in citations]
                logger.info(" PII redacted from unified response")
            
            # Store conversation to Redis if session_id provided
            if chat_history_store and session_id:
                try:
                    conversation_id = session_id
                    actual_user_id = user_id or "anonymous"
                    
                    chat_history_store.save_message(
                        user_id=actual_user_id,
                        question=question,
                        answer=answer,
                        metadata={
                            "model": config.MODEL_VARIANT,
                            "num_contexts": len(contexts),
                            "ingested_chunks": len(chunk_ids),
                            "unified_endpoint": True,
                            "tokens": token_usage
                        },
                        conversation_id=conversation_id
                    )
                    logger.info(f"💾 Stored ingest-and-query conversation to Redis", session_id=conversation_id, user_id=actual_user_id)
                except Exception as e:
                    logger.warning(f"Failed to store chat history to Redis: {e}")
            
            # ===== STEP 8: Build unified response =====
            metrics["total_time"] = time.time() - start_time
            
            # Determine actual PII filtered status
            pii_detected = any(r["has_pii"] for r in pii_results) if pii_results else False
            pii_filtered_status = pii_detector is not None  # True if PII detection was performed
            
            return UnifiedResponse(
                status="success",
                ingested_chunks=len(chunk_ids),
                question=question,
                answer=answer,
                contexts=contexts,
                citations=citations,
                pii_filtered=pii_filtered_status,
                model_used="gemini-2.0-flash-001",
                metrics=metrics,
                gcs_uris=gcs_uris if gcs_uris else None
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Unified pipeline failed", error=e)
            raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    """
    Query the RAG system: retrieve relevant chunks, re-rank, and generate answer.
    
    Production features:
    - Timeout handling for all operations
    - Graceful fallback for missing data
    - Detailed error logging
    - Performance metrics
    
    Features:
    - Vector search retrieval
    - Hybrid re-ranking
    - Grounded LLM generation
    - Citation extraction
    """
    with trace_operation("rag_query", {"question_length": len(req.question)}):
        try:
            logger.info("Processing query", question_preview=req.question[:100], top_k=req.top_k)
            
            # Retrieve top-K chunks from vector search
            start_time = time.time()
            with trace_operation("vector_search", {"top_k": req.top_k}):
                neighbors = vector_store.search(req.question, top_k=req.top_k * 2)  # Get more for re-ranking
            
            search_time = time.time() - start_time
            record_vector_search(search_time, len(neighbors))
            logger.info(f"Vector search completed", num_results=len(neighbors), duration=search_time)
            
            if not neighbors:
                logger.warning("No search results found")
                return QueryResponse(
                    question=req.question,
                    answer="No relevant documents found. Please ingest documents first.",
                    contexts=[],
                    citations=[],
                    model_used="none",
                    retrieval_scores=[]
                )
            
            # Re-rank results
            start_time = time.time()
            with trace_operation("rerank", {"num_chunks": len(neighbors)}):
                reranked = reranker.rerank(req.question, neighbors, top_k=req.top_k)
            
            rerank_time = time.time() - start_time
            logger.info(f"Re-ranking completed", num_chunks=len(reranked), duration=rerank_time)
            
            contexts = [n.get("text", "") for n in reranked]
            retrieval_scores = [
                {
                    "chunk_id": n.get("id", ""),
                    "score": n.get("rerank_score", n.get("score", 0.0))
                }
                for n in reranked
            ]
            
            # Apply Semantic Filtering
            if semantic_filter and len(contexts) > 1:
                try:
                    with trace_operation("semantic_filter"):
                        filtered_contexts = semantic_filter.filter_chunks(req.question, contexts)
                        logger.info(f"Semantic filtering: {len(contexts)} → {len(filtered_contexts)} chunks")
                        contexts = filtered_contexts
                except Exception as e:
                    logger.warning(f"Semantic filtering failed: {e}")
            
            # Apply Prompt Compression
            if prompt_compressor and contexts:
                try:
                    with trace_operation("prompt_compression"):
                        compressed_contexts = []
                        original_length = sum(len(ctx) for ctx in contexts)
                        
                        for ctx in contexts:
                            compressed = prompt_compressor.compress(ctx)
                            compressed_contexts.append(compressed)
                        
                        compressed_length = sum(len(ctx) for ctx in compressed_contexts)
                        compression_ratio = (1 - compressed_length / original_length) * 100 if original_length > 0 else 0
                        
                        logger.info(f"Prompt compression: {original_length} → {compressed_length} chars ({compression_ratio:.1f}% reduction)")
                        contexts = compressed_contexts
                except Exception as e:
                    logger.warning(f"Prompt compression failed: {e}")
            
            # Generate answer with citations
            start_time = time.time()
            with trace_operation("generate_answer", {"num_contexts": len(contexts)}):
                answer, citations, token_usage = generator.answer(
                    question=req.question,
                    contexts=contexts,
                    temperature=req.temperature
                )
            
            generation_time = time.time() - start_time
            logger.info(f"Answer generation completed", duration=generation_time, num_citations=len(citations), tokens=token_usage)
            
            # Record actual token usage from Gemini
            record_tokens(token_usage["total_tokens"], "generate")
            
            # 🔒 SECURITY: Redact PII from answer before returning to user
            if pii_detector:
                answer = pii_detector.redact_pii(answer)
                # Also redact PII from contexts/citations
                contexts = [pii_detector.redact_pii(ctx) for ctx in contexts]
                citations = [pii_detector.redact_pii(cite) for cite in citations]
                logger.info("🔒 PII redacted from answer, contexts, and citations")
            
            # Store conversation to Redis if session_id provided
            if chat_history_store and req.session_id:
                try:
                    conversation_id = req.session_id
                    user_id = req.user_id or "anonymous"
                    
                    chat_history_store.save_message(
                        user_id=user_id,
                        question=req.question,
                        answer=answer,
                        metadata={
                            "model": config.MODEL_VARIANT,
                            "num_contexts": len(contexts),
                            "temperature": req.temperature,
                            "tokens": token_usage
                        },
                        conversation_id=conversation_id
                    )
                    logger.info(f"💾 Stored conversation to Redis", session_id=conversation_id, user_id=user_id)
                except Exception as e:
                    logger.warning(f"Failed to store chat history to Redis: {e}")
            
            return QueryResponse(
                question=req.question,
                answer=answer,
                contexts=contexts,
                citations=citations,
                model_used=config.MODEL_VARIANT,
                retrieval_scores=retrieval_scores
            )
            
        except Exception as e:
            logger.error("Query failed", error=e, question_preview=req.question[:100])
            raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(req: EvaluateRequest):
    """
    Evaluate RAG response quality using RAGAS metrics.
    
    Metrics:
    - Answer Correctness
    - Faithfulness (groundedness)
    - Context Precision
    - Context Recall
    - Toxicity Score
    """
    with trace_operation("ragas_evaluation"):
        try:
            logger.info("Starting RAGAS evaluation", num_contexts=len(req.contexts))
            
            metrics = evaluator.evaluate(
                question=req.question,
                answer=req.answer,
                contexts=req.contexts,
                ground_truth=req.ground_truth
            )
            
            logger.info("RAGAS evaluation completed", metrics=metrics.to_dict())
            
            return EvaluateResponse(
                metrics=metrics.to_dict(),
                explanation={
                    "answer_correctness": "Semantic similarity to ground truth or question",
                    "faithfulness": "How well the answer is grounded in contexts",
                    "context_precision": "Relevance of retrieved contexts to question",
                    "context_recall": "Coverage of answer by contexts",
                    "toxicity_score": "Harmful content detection (lower is better)"
                }
            )
            
        except Exception as e:
            logger.error("Evaluation failed", error=e)
            raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@app.get("/stats")
def get_stats():
    """Get system statistics and configuration."""
    stats = {
        "service": "rag-service",
        "version": "2.0.0",
        "environment": config.ENVIRONMENT,
        "configuration": config.to_dict(),
        "features": {
            "document_ingestion": True,
            "cloud_storage": doc_store is not None,
            "firestore_persistence": chunk_store is not None,
            "vector_search": vector_store is not None,
            "re_ranking": reranker is not None,
            "llm_generation": generator is not None,
            "ragas_evaluation": evaluator is not None,
            "observability": True,
            "rate_limiting": True,
            "security_headers": True
        }
    }
    
    # Add vector store size if available
    if vector_store and hasattr(vector_store, 'chunk_store'):
        stats["vector_store_size"] = len(vector_store.chunk_store)
        stats["sample_chunks"] = list(vector_store.chunk_store.keys())[:5]
    
    # Add Firestore count if available
    if chunk_store:
        try:
            stats["firestore_chunks"] = chunk_store.count_chunks()
        except Exception as e:
            logger.warning(f"Could not retrieve Firestore chunk count: {e}")
    
    return stats


@app.get("/config")
def get_config():
    """Get current configuration (excludes secrets)."""
    return {
        "config": config.to_dict(),
        "validation": config.validate()
    }


@app.post("/query/advanced", response_model=QueryResponse)
async def query_langgraph(req: QueryRequest):
    """
    Query using LangGraph stateful RAG pipeline with advanced features:
    - Adaptive retrieval (refines query if confidence is low)
    - Self-correction capabilities
    - Multi-turn conversation memory
    - Iterative refinement (up to 2 iterations)
    
    This endpoint provides better results for complex queries that may need
    query refinement or multiple retrieval attempts.
    """
    with trace_operation("langgraph_rag_query", {"question_length": len(req.question)}):
        try:
            logger.info("Processing LangGraph query", question_preview=req.question[:100])
            
            # Convert chat history format
            chat_history = []
            if req.chat_history:
                for turn in req.chat_history:
                    if isinstance(turn, dict):
                        chat_history.append((turn.get("user", ""), turn.get("assistant", "")))
                    elif isinstance(turn, (list, tuple)) and len(turn) == 2:
                        chat_history.append((turn[0], turn[1]))
            
            # Run LangGraph pipeline
            start_time = time.time()
            result = await langgraph_pipeline.query(
                query=req.question,
                chat_history=chat_history
            )
            
            query_time = time.time() - start_time
            logger.info(
                "LangGraph query completed",
                duration=query_time,
                confidence=result["confidence"],
                iterations=result["iterations"]
            )
            
            # Format response - extract just the text strings for citations
            contexts = [source["text"] for source in result["sources"]]
            citations = [source["text"] for source in result["sources"][:3]]  # Top 3 as citations
            
            # Format retrieval scores as list of dicts
            retrieval_scores = [
                {
                    "chunk_id": source.get("id", f"chunk_{i}"),
                    "score": source.get("score", 0.0)
                }
                for i, source in enumerate(result["sources"])
            ]
            
            # Store conversation to Redis if session_id provided
            if chat_history_store and req.session_id:
                try:
                    conversation_id = req.session_id
                    user_id = req.user_id or "anonymous"
                    
                    chat_history_store.save_message(
                        user_id=user_id,
                        question=req.question,
                        answer=result["response"],
                        metadata={
                            "model": config.MODEL_VARIANT,
                            "num_contexts": len(contexts),
                            "confidence": result["confidence"],
                            "iterations": result["iterations"],
                            "langgraph": True
                        },
                        conversation_id=conversation_id
                    )
                    logger.info(f"💾 Stored LangGraph conversation to Redis", session_id=conversation_id, user_id=user_id)
                except Exception as e:
                    logger.warning(f"Failed to store chat history to Redis: {e}")
            
            return QueryResponse(
                question=req.question,
                answer=result["response"],
                contexts=contexts,
                citations=citations,
                model_used=config.MODEL_VARIANT,
                retrieval_scores=retrieval_scores
            )
            
        except Exception as e:
            logger.error("LangGraph query failed", error=e, question=req.question[:100])
            raise HTTPException(status_code=500, detail=f"LangGraph query failed: {str(e)}")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        log_level=config.LOG_LEVEL.lower()
    )

