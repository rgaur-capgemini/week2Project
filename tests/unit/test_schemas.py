"""Additional tests for RAG schemas and data models."""

import pytest
from pydantic import ValidationError
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.unit
def test_query_request_validation():
    """Test QueryRequest schema validation."""
    from app.rag.schemas import QueryRequest
    
    # Valid request
    request = QueryRequest(
        question="What is machine learning?",
        top_k=5
    )
    assert request.question == "What is machine learning?"
    assert request.top_k == 5


@pytest.mark.unit
def test_query_request_defaults():
    """Test QueryRequest default values."""
    from app.rag.schemas import QueryRequest
    
    request = QueryRequest(question="Test question")
    assert request.top_k == 5  # default value
    assert request.session_id is None


@pytest.mark.unit
def test_query_response_schema():
    """Test QueryResponse schema."""
    from app.rag.schemas import QueryResponse
    
    response = QueryResponse(
        answer="Machine learning is a subset of AI.",
        contexts=["Context 1", "Context 2"],
        metadata={"model": "gemini-pro", "tokens": 50}
    )
    assert response.answer == "Machine learning is a subset of AI."
    assert len(response.contexts) == 2


@pytest.mark.unit
def test_ingest_response_schema():
    """Test IngestResponse schema."""
    from app.rag.schemas import IngestResponse
    
    response = IngestResponse(
        status="success",
        document_id="doc123",
        chunks_created=10,
        message="Document ingested successfully"
    )
    assert response.status == "success"
    assert response.chunks_created == 10


@pytest.mark.unit
def test_unified_response_schema():
    """Test UnifiedResponse schema."""
    from app.rag.schemas import UnifiedResponse
    
    response = UnifiedResponse(
        answer="Test answer",
        contexts=["Context 1"],
        chunks=5,
        tokens=100,
        model="gemini-pro"
    )
    assert response.answer == "Test answer"
    assert response.tokens == 100


@pytest.mark.unit
def test_evaluate_request_schema():
    """Test EvaluateRequest schema."""
    from app.rag.schemas import EvaluateRequest
    
    request = EvaluateRequest(
        question="What is AI?",
        answer="AI is artificial intelligence.",
        contexts=["Context about AI"],
        ground_truth="AI stands for artificial intelligence."
    )
    assert request.question == "What is AI?"
    assert len(request.contexts) == 1


@pytest.mark.unit
def test_evaluate_response_schema():
    """Test EvaluateResponse schema."""
    from app.rag.schemas import EvaluateResponse
    
    response = EvaluateResponse(
        scores={
            "faithfulness": 0.95,
            "answer_relevancy": 0.90,
            "context_precision": 0.85
        }
    )
    assert response.scores["faithfulness"] == 0.95
    assert len(response.scores) == 3


@pytest.mark.unit
def test_query_request_invalid_top_k():
    """Test QueryRequest with invalid top_k."""
    from app.rag.schemas import QueryRequest
    
    with pytest.raises(ValidationError):
        QueryRequest(question="Test", top_k=-1)


@pytest.mark.unit
def test_query_request_empty_question():
    """Test QueryRequest with empty question."""
    from app.rag.schemas import QueryRequest
    
    with pytest.raises(ValidationError):
        QueryRequest(question="", top_k=5)


@pytest.mark.unit
def test_ingest_response_optional_fields():
    """Test IngestResponse with optional fields."""
    from app.rag.schemas import IngestResponse
    
    response = IngestResponse(
        status="success",
        document_id="doc123",
        chunks_created=5
    )
    assert response.message is None or isinstance(response.message, str)


@pytest.mark.unit
def test_query_response_with_metadata():
    """Test QueryResponse with metadata."""
    from app.rag.schemas import QueryResponse
    
    metadata = {
        "model": "gemini-pro",
        "tokens": 150,
        "response_time": 1.5,
        "sources": ["doc1.pdf", "doc2.txt"]
    }
    
    response = QueryResponse(
        answer="Test answer",
        contexts=["Context"],
        metadata=metadata
    )
    
    assert response.metadata["model"] == "gemini-pro"
    assert response.metadata["tokens"] == 150


@pytest.mark.unit
def test_evaluate_request_optional_ground_truth():
    """Test EvaluateRequest without ground truth."""
    from app.rag.schemas import EvaluateRequest
    
    request = EvaluateRequest(
        question="What is AI?",
        answer="AI is artificial intelligence.",
        contexts=["Context about AI"]
    )
    assert request.ground_truth is None or isinstance(request.ground_truth, str)


@pytest.mark.unit
def test_unified_response_optional_fields():
    """Test UnifiedResponse with optional fields."""
    from app.rag.schemas import UnifiedResponse
    
    response = UnifiedResponse(
        answer="Test answer",
        contexts=[],
        chunks=0,
        tokens=50
    )
    assert response.model is None or isinstance(response.model, str)


@pytest.mark.unit
def test_schema_json_serialization():
    """Test schema JSON serialization."""
    from app.rag.schemas import QueryRequest, QueryResponse
    
    request = QueryRequest(question="Test", top_k=5)
    json_str = request.model_dump_json()
    assert isinstance(json_str, str)
    assert "Test" in json_str


@pytest.mark.unit
def test_schema_dict_conversion():
    """Test schema dict conversion."""
    from app.rag.schemas import QueryResponse
    
    response = QueryResponse(
        answer="Test",
        contexts=["Context"],
        metadata={"key": "value"}
    )
    
    data = response.model_dump()
    assert isinstance(data, dict)
    assert data["answer"] == "Test"
