"""
Week 5 - Pydantic schemas for Agent, Multimodal, and CSV Ingestion APIs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════
# Agent schemas
# ══════════════════════════════════════════════

class ConversationTurn(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class AgentQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4096, description="User question or instruction")
    session_id: Optional[str] = Field(None, description="Session ID for conversation tracking")
    conversation_history: Optional[List[ConversationTurn]] = Field(
        None, description="Prior conversation turns"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Extra context (e.g., gcs_uri, image_uri)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What are the key trends in the uploaded sales CSV?",
                "session_id": "sess_abc123",
                "metadata": {"gcs_uri": "gs://my-bucket/sales.csv"},
            }
        }


class ToolCallLog(BaseModel):
    tool: str
    args: Dict[str, Any]
    result_preview: str


class AgentQueryResponse(BaseModel):
    answer: str
    tool_calls: List[ToolCallLog] = []
    sources: List[str] = []
    intent: Optional[str] = None
    agent_used: Optional[str] = None
    latency_ms: int
    session_id: Optional[str] = None
    model: Optional[str] = None


class BatchAgentRequest(BaseModel):
    queries: List[AgentQueryRequest] = Field(..., min_length=1, max_length=20)


class BatchAgentResponse(BaseModel):
    results: List[AgentQueryResponse]
    total_queries: int
    total_latency_ms: int


# ══════════════════════════════════════════════
# CSV Ingestion schemas
# ══════════════════════════════════════════════

class CSVEmbedRequest(BaseModel):
    gcs_uri: str = Field(..., description="GCS URI of the CSV to embed, e.g. gs://bucket/file.csv")
    source_label: Optional[str] = Field(None, description="Human-readable label for this dataset")
    chunk_strategy: str = Field("row", description="'row' or 'group'")
    group_column: Optional[str] = Field(None, description="Column to group by (for 'group' strategy)")
    max_rows: int = Field(10_000, ge=1, le=100_000, description="Max rows to embed")

    class Config:
        json_schema_extra = {
            "example": {
                "gcs_uri": "gs://btoproject-486405-486604-csv-data/sales_2025.csv",
                "chunk_strategy": "row",
                "max_rows": 5000,
            }
        }


class CSVEmbedResponse(BaseModel):
    status: str
    gcs_uri: str
    rows_processed: int = 0
    chunks_embedded: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None


# ══════════════════════════════════════════════
# Multimodal schemas
# ══════════════════════════════════════════════

class MultimodalQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4096)
    image_sources: Optional[List[str]] = Field(
        None, description="List of GCS URIs or HTTP image URLs"
    )
    enable_rag: bool = Field(True, description="Augment with RAG document retrieval")
    image_task: str = Field(
        "describe",
        description="'describe' | 'ocr' | 'qa' | 'table' | 'classify'",
    )
    session_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What does this chart show? Compare with our Q4 targets.",
                "image_sources": ["gs://my-bucket/chart.png"],
                "enable_rag": True,
                "image_task": "describe",
            }
        }


class ImageAnalysisResult(BaseModel):
    source: str
    task: str
    description: Optional[str] = None
    extracted_text: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None
    raw_output: Optional[str] = None
    error: Optional[str] = None
    latency_ms: Optional[int] = None


class MultimodalQueryResponse(BaseModel):
    answer: str
    image_analyses: List[ImageAnalysisResult] = []
    rag_context: str = ""
    sources: List[str] = []
    mode: str = "multimodal_rag"
    latency_ms: int
    session_id: Optional[str] = None


class OCRRequest(BaseModel):
    image_sources: List[str] = Field(..., min_length=1, max_length=20)
    language_hint: str = Field("auto", description="Language hint for OCR, e.g. 'en', 'fr'")

    class Config:
        json_schema_extra = {
            "example": {
                "image_sources": ["gs://my-bucket/scan.pdf"],
                "language_hint": "en",
            }
        }


class OCRResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_images: int
    latency_ms: int


# ══════════════════════════════════════════════
# Enhanced RAG schemas
# ══════════════════════════════════════════════

class EnhancedRAGRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4096)
    session_id: Optional[str] = None
    enable_decomposition: bool = Field(True, description="Break complex questions into sub-queries")
    enable_self_eval: bool = Field(True, description="Score the answer quality")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What are the compliance requirements for ISO 27001 and how do they relate to our policies?",
                "enable_decomposition": True,
            }
        }


class EnhancedRAGResponse(BaseModel):
    answer: str
    sources: List[str] = []
    sub_queries: List[str] = []
    retrieval_count: int = 0
    evaluation: Dict[str, Any] = {}
    latency_ms: int
    session_id: Optional[str] = None
    model: Optional[str] = None
