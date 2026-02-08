"""
Integration tests for main API endpoints.
Tests the complete request/response flow.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import json


@pytest.fixture
def mock_all_dependencies(mocker):
    """Mock all external dependencies."""
    # Mock Secret Manager
    mock_sm = mocker.patch("google.cloud.secretmanager_v1.SecretManagerServiceClient")
    mock_sm_instance = Mock()
    mock_sm_instance.access_secret_version.return_value = Mock(payload=Mock(data=b"test-secret"))
    mock_sm.return_value = mock_sm_instance
    
    # Mock Vertex AI
    mocker.patch("google.cloud.aiplatform.init")
    
    # Mock Redis
    mock_redis = mocker.patch("redis.Redis")
    mock_redis_instance = Mock()
    mock_redis_instance.ping.return_value = True
    mock_redis_instance.get.return_value = None
    mock_redis.return_value = mock_redis_instance
    
    # Mock Firestore
    mocker.patch("google.cloud.firestore.Client")
    
    # Mock GCS
    mocker.patch("google.cloud.storage.Client")
    
    yield


@pytest.fixture
def client(mock_all_dependencies):
    """Create test client."""
    from app.main import app
    return TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy" or "message" in data
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestConfigEndpoint:
    """Test configuration endpoint."""
    
    def test_config_endpoint(self, client, mocker):
        """Test config endpoint returns OAuth client ID."""
        # Mock the secret manager to return a client ID
        mock_sm = mocker.patch("app.auth.oidc._get_oauth_client_id")
        mock_sm.return_value = "test-client-id.apps.googleusercontent.com"
        
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "googleClientId" in data
        assert "apps.googleusercontent.com" in data["googleClientId"]


class TestQueryEndpoint:
    """Test query endpoint."""
    
    def test_query_endpoint_unauthorized(self, client):
        """Test query without authentication."""
        response = client.post(
            "/query",
            json={"question": "What is AI?"}
        )
        # Should require authentication
        assert response.status_code in [401, 422]  # 422 if validation fails first
    
    def test_query_endpoint_with_auth(self, client, mocker):
        """Test query with authentication."""
        # Mock authentication
        mock_verify = mocker.patch("app.auth.jwt_handler.verify_token")
        mock_verify.return_value = {
            "sub": "test-user",
            "email": "test@example.com",
            "role": "user"
        }
        
        # Mock RAG components
        mock_embeddings = mocker.patch("app.rag.embeddings.EmbeddingGenerator.generate")
        mock_embeddings.return_value = [0.1] * 768
        
        mock_search = mocker.patch("app.rag.vector_store.VectorStore.search")
        mock_search.return_value = [
            Mock(id="doc1-0", distance=0.1)
        ]
        
        mock_generate = mocker.patch("app.rag.generator.AnswerGenerator.generate")
        mock_generate.return_value = "AI is artificial intelligence."
        
        response = client.post(
            "/query",
            json={"question": "What is AI?"},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
    
    def test_query_invalid_payload(self, client, mocker):
        """Test query with invalid payload."""
        mock_verify = mocker.patch("app.auth.jwt_handler.verify_token")
        mock_verify.return_value = {"sub": "test-user", "email": "test@example.com"}
        
        response = client.post(
            "/query",
            json={},  # Missing question
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 422


class TestIngestEndpoint:
    """Test document ingestion endpoint."""
    
    def test_ingest_unauthorized(self, client):
        """Test ingest without authentication."""
        response = client.post(
            "/ingest",
            files={"files": ("test.txt", b"Test content", "text/plain")}
        )
        assert response.status_code in [401, 422]
    
    def test_ingest_with_auth(self, client, mocker):
        """Test document ingestion with authentication."""
        # Mock authentication
        mock_verify = mocker.patch("app.auth.jwt_handler.verify_token")
        mock_verify.return_value = {
            "sub": "test-user",
            "email": "test@example.com",
            "role": "admin"
        }
        
        # Mock components
        mocker.patch("app.rag.chunker.extract_and_chunk", return_value=[
            {"id": "test-0", "text": "Test chunk", "metadata": {}}
        ])
        mocker.patch("app.rag.embeddings.EmbeddingGenerator.generate_batch", 
                    return_value=[[0.1] * 768])
        mocker.patch("app.rag.vector_store.VectorStore.add_batch", return_value=True)
        mocker.patch("app.storage.gcs_store.GCSStore.upload_file", 
                    return_value="gs://bucket/test.txt")
        
        response = client.post(
            "/ingest",
            files={"files": ("test.txt", b"Test content", "text/plain")},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "chunks_created" in data
    
    def test_ingest_non_admin(self, client, mocker):
        """Test that non-admin cannot ingest."""
        mock_verify = mocker.patch("app.auth.jwt_handler.verify_token")
        mock_verify.return_value = {
            "sub": "test-user",
            "email": "test@example.com",
            "role": "user"  # Not admin
        }
        
        response = client.post(
            "/ingest",
            files={"files": ("test.txt", b"Test content", "text/plain")},
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Should deny non-admin
        assert response.status_code in [403, 401]


class TestUnifiedEndpoint:
    """Test unified RAG endpoint."""
    
    def test_unified_query(self, client, mocker):
        """Test unified query mode."""
        mock_verify = mocker.patch("app.auth.jwt_handler.verify_token")
        mock_verify.return_value = {"sub": "test-user", "email": "test@example.com"}
        
        # Mock RAG pipeline
        mocker.patch("app.rag.embeddings.EmbeddingGenerator.generate", 
                    return_value=[0.1] * 768)
        mocker.patch("app.rag.vector_store.VectorStore.search", 
                    return_value=[Mock(id="doc1-0")])
        mocker.patch("app.rag.generator.AnswerGenerator.generate", 
                    return_value="Answer")
        
        response = client.post(
            "/unified",
            json={
                "mode": "query",
                "question": "What is AI?"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data or "response" in data
    
    def test_unified_ingest(self, client, mocker):
        """Test unified ingest mode."""
        mock_verify = mocker.patch("app.auth.jwt_handler.verify_token")
        mock_verify.return_value = {
            "sub": "test-user",
            "email": "test@example.com",
            "role": "admin"
        }
        
        # Mock ingestion
        mocker.patch("app.rag.chunker.extract_and_chunk", return_value=[
            {"id": "test-0", "text": "Test", "metadata": {}}
        ])
        mocker.patch("app.rag.embeddings.EmbeddingGenerator.generate_batch", 
                    return_value=[[0.1] * 768])
        mocker.patch("app.rag.vector_store.VectorStore.add_batch", return_value=True)
        mocker.patch("app.storage.gcs_store.GCSStore.upload_file", 
                    return_value="gs://bucket/test.txt")
        
        response = client.post(
            "/unified",
            files={"files": ("test.txt", b"Test", "text/plain")},
            data={"mode": "ingest"},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200


class TestRoleBasedAccess:
    """Test role-based access control."""
    
    def test_admin_endpoints_require_admin(self, client, mocker):
        """Test that admin endpoints require admin role."""
        # Regular user
        mock_verify = mocker.patch("app.auth.jwt_handler.verify_token")
        mock_verify.return_value = {
            "sub": "test-user",
            "email": "user@example.com",
            "role": "user"
        }
        
        # Try to access admin-only endpoint
        response = client.post(
            "/ingest",
            files={"files": ("test.txt", b"Test", "text/plain")},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code in [403, 401]
    
    def test_admin_has_full_access(self, client, mocker):
        """Test that admin has access to all endpoints."""
        mock_verify = mocker.patch("app.auth.jwt_handler.verify_token")
        mock_verify.return_value = {
            "sub": "admin-user",
            "email": "admin@example.com",
            "role": "admin"
        }
        
        # Mock dependencies
        mocker.patch("app.rag.chunker.extract_and_chunk", return_value=[])
        mocker.patch("app.rag.embeddings.EmbeddingGenerator.generate_batch", 
                    return_value=[])
        mocker.patch("app.rag.vector_store.VectorStore.add_batch", return_value=True)
        mocker.patch("app.storage.gcs_store.GCSStore.upload_file", 
                    return_value="gs://bucket/test.txt")
        
        # Admin should be able to ingest
        response = client.post(
            "/ingest",
            files={"files": ("test.txt", b"Test", "text/plain")},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling."""
    
    def test_internal_server_error(self, client, mocker):
        """Test handling of internal errors."""
        mock_verify = mocker.patch("app.auth.jwt_handler.verify_token")
        mock_verify.return_value = {"sub": "test-user", "email": "test@example.com"}
        
        # Mock component to raise error
        mocker.patch("app.rag.embeddings.EmbeddingGenerator.generate", 
                    side_effect=Exception("Test error"))
        
        response = client.post(
            "/query",
            json={"question": "Test"},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 500
    
    def test_validation_error(self, client, mocker):
        """Test validation errors."""
        mock_verify = mocker.patch("app.auth.jwt_handler.verify_token")
        mock_verify.return_value = {"sub": "test-user", "email": "test@example.com"}
        
        # Send invalid data
        response = client.post(
            "/query",
            json={"invalid_field": "value"},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 422


@pytest.mark.integration
class TestEndToEndFlow:
    """Test complete end-to-end workflows."""
    
    def test_ingest_and_query_flow(self, client, mocker):
        """Test complete ingest -> query flow."""
        # Setup admin auth
        mock_verify = mocker.patch("app.auth.jwt_handler.verify_token")
        mock_verify.return_value = {
            "sub": "admin",
            "email": "admin@example.com",
            "role": "admin"
        }
        
        # Mock all components
        mocker.patch("app.rag.chunker.extract_and_chunk", return_value=[
            {"id": "doc-0", "text": "AI is artificial intelligence", "metadata": {}}
        ])
        mocker.patch("app.rag.embeddings.EmbeddingGenerator.generate_batch", 
                    return_value=[[0.1] * 768])
        mocker.patch("app.rag.embeddings.EmbeddingGenerator.generate", 
                    return_value=[0.1] * 768)
        mocker.patch("app.rag.vector_store.VectorStore.add_batch", return_value=True)
        mocker.patch("app.rag.vector_store.VectorStore.search", 
                    return_value=[Mock(id="doc-0")])
        mocker.patch("app.rag.generator.AnswerGenerator.generate", 
                    return_value="AI is artificial intelligence")
        mocker.patch("app.storage.gcs_store.GCSStore.upload_file", 
                    return_value="gs://bucket/doc.txt")
        mocker.patch("app.storage.firestore_store.FirestoreStore.add_document")
        
        # Ingest document
        ingest_response = client.post(
            "/ingest",
            files={"files": ("doc.txt", b"AI is artificial intelligence", "text/plain")},
            headers={"Authorization": "Bearer admin-token"}
        )
        assert ingest_response.status_code == 200
        
        # Query
        query_response = client.post(
            "/query",
            json={"question": "What is AI?"},
            headers={"Authorization": "Bearer admin-token"}
        )
        assert query_response.status_code == 200
        data = query_response.json()
        assert "answer" in data
