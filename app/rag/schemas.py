
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class QueryRequest(BaseModel):
    question: str = Field(..., description="User's question")
    top_k: int = Field(default=5, description="Number of chunks to retrieve", ge=1, le=20)
    temperature: float = Field(default=0.2, description="LLM temperature", ge=0.0, le=1.0)
    chat_history: Optional[List[Dict[str, str]]] = Field(default=None, description="Previous conversation turns")

class QueryResponse(BaseModel):
    question: str
    answer: str
    contexts: List[str]
    citations: List[str]
    model_used: str = "gemini-2.0-flash-001"
    retrieval_scores: List[Dict] = []

class IngestResponse(BaseModel):
    ingested: int
    chunk_ids: List[str]
    message: str = "Ingestion successful"
    gcs_uris: Optional[List[str]] = None  # Cloud Storage URIs for uploaded documents

class UnifiedResponse(BaseModel):
    """Response for unified ingest-and-query endpoint"""
    status: str = "success"
    ingested_chunks: int
    question: str
    answer: str
    contexts: List[str]
    citations: List[str]
    pii_filtered: bool = True
    model_used: str = "gemini-2.0-flash-001"
    metrics: Dict = {}  # Timing and token metrics
    gcs_uris: Optional[List[str]] = None

class EvaluateRequest(BaseModel):
    question: str
    answer: str
    contexts: List[str]
    ground_truth: Optional[str] = None

class EvaluateResponse(BaseModel):
    metrics: Dict
    explanation: Dict
