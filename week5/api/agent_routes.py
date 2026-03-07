"""
Week 5 - Agent API Routes

Endpoints:
  POST /api/v5/agent/query       - Single query through the agentic pipeline
  POST /api/v5/agent/batch       - Batch of queries
  GET  /api/v5/agent/health      - Agent service health check
  POST /api/v5/agent/csv/embed   - Trigger CSV embedding into Vector Search
  POST /api/v5/rag/query         - Enhanced RAG query with decomposition + self-eval
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from week5.api.schemas import (
    AgentQueryRequest,
    AgentQueryResponse,
    BatchAgentRequest,
    BatchAgentResponse,
    CSVEmbedRequest,
    CSVEmbedResponse,
    EnhancedRAGRequest,
    EnhancedRAGResponse,
    ToolCallLog,
)

logger = logging.getLogger(__name__)

agent_router = APIRouter(prefix="/api/v5/agent", tags=["Week5 - Agentic AI"])
rag_router = APIRouter(prefix="/api/v5/rag", tags=["Week5 - Enhanced RAG"])

# ── Lazy singleton instances ───────────────────
_orchestrator = None
_rag_pipeline = None
_csv_embedder = None


def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        from app.config import config
        from week5.agentic_ai.orchestrator import MultiAgentOrchestrator

        _orchestrator = MultiAgentOrchestrator(
            project_id=config.PROJECT_ID,
            location=config.VERTEX_LOCATION,
            model_name=config.MODEL_VARIANT,
        )
    return _orchestrator


def _get_rag_pipeline():
    global _rag_pipeline
    if _rag_pipeline is None:
        from app.config import config
        from week5.rag.enhanced_rag_pipeline import EnhancedRAGPipeline

        _rag_pipeline = EnhancedRAGPipeline(
            project_id=config.PROJECT_ID,
            location=config.VERTEX_LOCATION,
            model_name=config.MODEL_VARIANT,
        )
    return _rag_pipeline


def _get_csv_embedder():
    global _csv_embedder
    if _csv_embedder is None:
        from app.config import config
        from week5.rag.csv_embedder import CSVEmbedder

        _csv_embedder = CSVEmbedder(
            project_id=config.PROJECT_ID,
            location=config.VERTEX_LOCATION,
        )
    return _csv_embedder


# ══════════════════════════════════════════════
# Agent Routes
# ══════════════════════════════════════════════

@agent_router.get("/health")
async def agent_health():
    """Health check for the Week 5 agent service."""
    return {
        "status": "healthy",
        "service": "week5-agentic-ai",
        "version": "5.0.0",
        "features": [
            "agentic_ai",
            "csv_rag",
            "multimodal",
            "enhanced_rag",
        ],
    }


@agent_router.post("/query", response_model=AgentQueryResponse)
async def agent_query(request: AgentQueryRequest):
    """
    Run a single query through the Multi-Agent Orchestrator.

    The orchestrator classifies the intent and routes to the correct agent
    (RAG, CSV Analysis, Multimodal, or FinOps), then returns a structured answer.
    """
    try:
        orchestrator = _get_orchestrator()

        history = None
        if request.conversation_history:
            history = [
                {"role": t.role, "content": t.content}
                for t in request.conversation_history
            ]

        result = orchestrator.run(
            user_query=request.query,
            session_id=request.session_id,
            conversation_history=history,
            metadata=request.metadata or {},
        )

        return AgentQueryResponse(
            answer=result.get("answer", ""),
            tool_calls=[
                ToolCallLog(**tc) for tc in result.get("tool_calls", [])
            ],
            sources=result.get("sources", []),
            intent=result.get("intent"),
            agent_used=result.get("agent_used"),
            latency_ms=result.get("latency_ms", 0),
            session_id=result.get("session_id"),
            model=result.get("model"),
        )

    except Exception as exc:
        logger.error(f"Agent query failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Agent query failed: {str(exc)}")


@agent_router.post("/batch", response_model=BatchAgentResponse)
async def agent_batch_query(request: BatchAgentRequest):
    """
    Run a batch of queries through the orchestrator.
    Processes up to 20 queries sequentially.
    """
    try:
        orchestrator = _get_orchestrator()
        start = time.time()

        queries = []
        for q in request.queries:
            history = None
            if q.conversation_history:
                history = [{"role": t.role, "content": t.content} for t in q.conversation_history]
            queries.append(
                {
                    "query": q.query,
                    "session_id": q.session_id,
                    "metadata": q.metadata or {},
                }
            )

        raw_results = orchestrator.run_batch(queries)
        results = []
        for r in raw_results:
            results.append(
                AgentQueryResponse(
                    answer=r.get("answer", ""),
                    tool_calls=[ToolCallLog(**tc) for tc in r.get("tool_calls", [])],
                    sources=r.get("sources", []),
                    intent=r.get("intent"),
                    agent_used=r.get("agent_used"),
                    latency_ms=r.get("latency_ms", 0),
                    session_id=r.get("session_id"),
                    model=r.get("model"),
                )
            )

        total_latency = int((time.time() - start) * 1000)
        return BatchAgentResponse(
            results=results,
            total_queries=len(results),
            total_latency_ms=total_latency,
        )

    except Exception as exc:
        logger.error(f"Batch agent query failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@agent_router.post("/csv/embed", response_model=CSVEmbedResponse)
async def embed_csv(request: CSVEmbedRequest, background_tasks: BackgroundTasks):
    """
    Trigger CSV embedding into Vertex AI Vector Search.

    The embedding runs in the background. Returns immediately with status.
    """
    import uuid

    task_id = str(uuid.uuid4())

    def _run_embed():
        try:
            embedder = _get_csv_embedder()
            embedder.chunk_strategy = request.chunk_strategy
            embedder.group_column = request.group_column
            result = embedder.embed_from_gcs(
                gcs_uri=request.gcs_uri,
                source_label=request.source_label,
                max_rows=request.max_rows,
            )
            logger.info(f"CSV embed task {task_id} complete: {result}")
        except Exception as exc:
            logger.error(f"CSV embed task {task_id} failed: {exc}")

    background_tasks.add_task(_run_embed)

    return CSVEmbedResponse(
        status="accepted",
        gcs_uri=request.gcs_uri,
        rows_processed=0,
        chunks_embedded=0,
    )


# ══════════════════════════════════════════════
# Enhanced RAG Routes
# ══════════════════════════════════════════════

@rag_router.post("/query", response_model=EnhancedRAGResponse)
async def enhanced_rag_query(request: EnhancedRAGRequest):
    """
    Run the Enhanced RAG pipeline with query decomposition and self-evaluation.

    Features over basic /query:
    - Multi-hop query decomposition
    - Source diversity filtering
    - Confidence scoring
    - Hallucination risk assessment
    """
    try:
        pipeline = _get_rag_pipeline()
        pipeline.enable_decomposition = request.enable_decomposition
        pipeline.enable_self_eval = request.enable_self_eval

        result = pipeline.query(
            question=request.question,
            session_id=request.session_id,
        )

        return EnhancedRAGResponse(
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            sub_queries=result.get("sub_queries", []),
            retrieval_count=result.get("retrieval_count", 0),
            evaluation=result.get("evaluation", {}),
            latency_ms=result.get("latency_ms", 0),
            session_id=result.get("session_id"),
            model=result.get("model"),
        )

    except Exception as exc:
        logger.error(f"Enhanced RAG query failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
