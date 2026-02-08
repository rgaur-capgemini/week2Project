"""Tests for main.py application startup and endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_all_services():
    """Mock all service dependencies."""
    with patch("app.main.VertexTextEmbedder") as mock_embedder, \
         patch("app.main.VertexVectorStore") as mock_vector, \
         patch("app.main.FirestoreChunkStore") as mock_firestore, \
         patch("app.main.GCSDocumentStore") as mock_gcs, \
         patch("app.main.GeminiGenerator") as mock_generator, \
         patch("app.main.HybridReranker") as mock_reranker, \
         patch("app.main.RAGASEvaluator") as mock_evaluator, \
         patch("app.main.PIIDetector") as mock_pii, \
         patch("app.main.LangGraphRAGPipeline") as mock_langgraph, \
         patch("app.main.ChatHistoryStore") as mock_history, \
         patch("app.main.AnalyticsCollector") as mock_analytics, \
         patch("app.main.PromptCompressor") as mock_compressor, \
         patch("app.main.SemanticFilter") as mock_filter:
        
        yield {
            "embedder": mock_embedder,
            "vector": mock_vector,
            "firestore": mock_firestore,
            "gcs": mock_gcs,
            "generator": mock_generator,
            "reranker": mock_reranker,
            "evaluator": mock_evaluator,
            "pii": mock_pii,
            "langgraph": mock_langgraph,
            "history": mock_history,
            "analytics": mock_analytics,
            "compressor": mock_compressor,
            "filter": mock_filter
        }


@pytest.fixture
def client(mock_all_services):
    """Create test client with mocked services."""
    from app.main import app
    return TestClient(app)


@pytest.mark.unit
def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "timestamp" in data


@pytest.mark.unit
def test_readiness_endpoint(client):
    """Test readiness check endpoint."""
    response = client.get("/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


@pytest.mark.unit
def test_liveness_endpoint(client):
    """Test liveness check endpoint."""
    response = client.get("/liveness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


@pytest.mark.unit
def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data


@pytest.mark.unit
def test_cors_headers(client):
    """Test CORS headers are properly set."""
    response = client.options(
        "/query",
        headers={"Origin": "http://localhost:4200"}
    )
    assert "access-control-allow-origin" in response.headers


@pytest.mark.unit
@patch("app.main.embedder")
@patch("app.main.vector_store")
@patch("app.main.reranker")
@patch("app.main.generator")
@patch("app.main.pii_detector")
def test_query_endpoint(mock_pii, mock_gen, mock_rerank, mock_vector, mock_embed, client):
    """Test query endpoint with mocked services."""
    # Setup mocks
    mock_pii.detect_and_redact.return_value = ("Test query", False)
    mock_embed.embed_query.return_value = [0.1] * 768
    mock_vector.search.return_value = [
        {"id": "1", "score": 0.9, "text": "Context 1"}
    ]
    mock_rerank.rerank.return_value = [
        {"id": "1", "score": 0.95, "text": "Context 1"}
    ]
    mock_gen.generate.return_value = {
        "answer": "Test answer",
        "tokens": 50
    }
    
    response = client.post(
        "/query",
        json={
            "question": "What is AI?",
            "top_k": 5
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data


@pytest.mark.unit
def test_ingest_endpoint_missing_file(client):
    """Test ingest endpoint with missing file."""
    response = client.post("/ingest")
    assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.unit
def test_stats_endpoint(client):
    """Test statistics endpoint."""
    with patch("app.main.vector_store") as mock_vector:
        mock_vector.get_stats.return_value = {
            "total_vectors": 100,
            "dimensions": 768
        }
        response = client.get("/stats")
        assert response.status_code == 200


@pytest.mark.unit
def test_delete_endpoint(client):
    """Test delete document endpoint."""
    with patch("app.main.vector_store") as mock_vector, \
         patch("app.main.chunk_store") as mock_chunk, \
         patch("app.main.doc_store") as mock_doc:
        
        mock_vector.delete_by_metadata.return_value = 5
        
        response = client.delete("/documents/test-doc.pdf")
        assert response.status_code == 200
        data = response.json()
        assert "chunks_deleted" in data
