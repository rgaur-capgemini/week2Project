"""
Week 5 - Multimodal API Routes

Endpoints:
  POST /api/v5/multimodal/query    - Combined image + text + RAG query
  POST /api/v5/multimodal/ocr      - Batch OCR for multiple images
  POST /api/v5/multimodal/describe - Describe images (no RAG)
  POST /api/v5/multimodal/upload   - Upload image bytes for analysis
"""

import base64
import logging
import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from week5.api.schemas import (
    MultimodalQueryRequest,
    MultimodalQueryResponse,
    OCRRequest,
    OCRResponse,
    ImageAnalysisResult,
)

logger = logging.getLogger(__name__)

multimodal_router = APIRouter(prefix="/api/v5/multimodal", tags=["Week5 - Multimodal"])

# ── Lazy singleton ─────────────────────────────
_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        from app.config import config
        from week5.multimodal.multimodal_pipeline import MultimodalPipeline

        _pipeline = MultimodalPipeline(
            project_id=config.PROJECT_ID,
            location=config.VERTEX_LOCATION,
            model_name=config.MODEL_VARIANT,
        )
    return _pipeline


# ══════════════════════════════════════════════
# Multimodal Routes
# ══════════════════════════════════════════════

@multimodal_router.get("/health")
async def multimodal_health():
    """Health check for the multimodal service."""
    return {
        "status": "healthy",
        "service": "week5-multimodal",
        "capabilities": ["ocr", "describe", "qa", "table_extraction", "classification"],
    }


@multimodal_router.post("/query", response_model=MultimodalQueryResponse)
async def multimodal_query(request: MultimodalQueryRequest):
    """
    Process a multimodal query combining images + RAG document context.

    Accepts GCS URIs or HTTP image URLs. Analyses images using Gemini Vision
    and optionally augments with document retrieval for richer answers.
    """
    try:
        pipeline = _get_pipeline()
        result = pipeline.process(
            question=request.question,
            image_sources=request.image_sources,
            enable_rag=request.enable_rag,
            image_task=request.image_task,
            session_id=request.session_id,
        )

        image_analyses = []
        for a in result.get("image_analyses", []):
            image_analyses.append(
                ImageAnalysisResult(
                    source=a.get("source", ""),
                    task=a.get("task", ""),
                    description=a.get("description"),
                    extracted_text=a.get("extracted_text"),
                    answer=a.get("answer"),
                    category=a.get("category"),
                    raw_output=a.get("raw_output"),
                    error=a.get("error"),
                    latency_ms=a.get("latency_ms"),
                )
            )

        return MultimodalQueryResponse(
            answer=result.get("answer", ""),
            image_analyses=image_analyses,
            rag_context=result.get("rag_context", ""),
            sources=result.get("sources", []),
            mode=result.get("mode", "multimodal_rag"),
            latency_ms=result.get("latency_ms", 0),
            session_id=result.get("session_id"),
        )

    except Exception as exc:
        logger.error(f"Multimodal query failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@multimodal_router.post("/upload")
async def multimodal_upload(
    question: str = Form(..., description="Question about the uploaded image(s)"),
    image_task: str = Form("describe", description="'describe' | 'ocr' | 'qa' | 'table' | 'classify'"),
    enable_rag: bool = Form(True),
    session_id: Optional[str] = Form(None),
    files: List[UploadFile] = File(..., description="Image files to analyse"),
):
    """
    Upload image files directly for multimodal analysis.

    Accepts JPEG, PNG, GIF, WEBP, PDF images.
    Max 10 files per request.
    """
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images per request.")

    raw_images = []
    for f in files:
        content = await f.read()
        mime = f.content_type or "image/jpeg"
        raw_images.append(
            {
                "bytes": content,
                "mime_type": mime,
                "label": f.filename or "uploaded_image",
            }
        )

    try:
        pipeline = _get_pipeline()
        result = pipeline.process(
            question=question,
            raw_images=raw_images,
            enable_rag=enable_rag,
            image_task=image_task,
            session_id=session_id,
        )

        image_analyses = []
        for a in result.get("image_analyses", []):
            image_analyses.append(
                ImageAnalysisResult(
                    source=a.get("source", ""),
                    task=a.get("task", ""),
                    description=a.get("description"),
                    extracted_text=a.get("extracted_text"),
                    answer=a.get("answer"),
                    category=a.get("category"),
                    error=a.get("error"),
                    latency_ms=a.get("latency_ms"),
                )
            )

        return MultimodalQueryResponse(
            answer=result.get("answer", ""),
            image_analyses=image_analyses,
            rag_context=result.get("rag_context", ""),
            sources=result.get("sources", []),
            mode=result.get("mode", "multimodal_rag"),
            latency_ms=result.get("latency_ms", 0),
            session_id=session_id,
        )

    except Exception as exc:
        logger.error(f"Upload multimodal query failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@multimodal_router.post("/ocr", response_model=OCRResponse)
async def batch_ocr(request: OCRRequest):
    """
    Perform OCR on multiple images in batch.
    Returns extracted text for each image.
    """
    start = time.time()
    try:
        pipeline = _get_pipeline()
        results = []

        for src in request.image_sources:
            result = pipeline.image_processor.extract_text(
                src, language_hint=request.language_hint
            )
            results.append(result)

        latency_ms = int((time.time() - start) * 1000)
        return OCRResponse(
            results=results,
            total_images=len(results),
            latency_ms=latency_ms,
        )

    except Exception as exc:
        logger.error(f"Batch OCR failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@multimodal_router.post("/describe")
async def describe_images(
    image_sources: List[str],
    detail_level: str = "standard",
    session_id: Optional[str] = None,
):
    """
    Describe a list of images without RAG augmentation.

    detail_level: 'brief' | 'standard' | 'detailed'
    """
    start = time.time()
    try:
        pipeline = _get_pipeline()
        results = pipeline.image_processor.batch_analyze(
            image_sources=image_sources,
            task="describe",
        )
        return {
            "descriptions": results,
            "total_images": len(results),
            "detail_level": detail_level,
            "latency_ms": int((time.time() - start) * 1000),
            "session_id": session_id,
        }
    except Exception as exc:
        logger.error(f"Describe images failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@multimodal_router.post("/invoice")
async def analyze_invoice(
    image_source: str,
    session_id: Optional[str] = None,
):
    """
    Specialised endpoint: Extract and analyse invoice data from an image.
    Uses OCR + RAG to cross-reference with pricing policies.
    """
    try:
        pipeline = _get_pipeline()
        result = pipeline.analyze_invoice(
            image_source=image_source, session_id=session_id
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@multimodal_router.post("/chart")
async def analyze_chart(
    image_source: str,
    question: str = "What trends and insights does this chart show?",
    session_id: Optional[str] = None,
):
    """
    Specialised endpoint: Analyse a chart image and correlate with document context.
    """
    try:
        pipeline = _get_pipeline()
        result = pipeline.analyze_chart(
            image_source=image_source, question=question, session_id=session_id
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
