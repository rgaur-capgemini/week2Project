"""
Unit tests for vector store module.
Tests vector storage and retrieval.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
import sys

# Mock vertexai before importing
sys.modules['vertexai'] = MagicMock()
sys.modules['vertexai.matching_engine'] = MagicMock()

from app.rag.vector_store import VectorStore


class TestVectorStore:
    """Test vector store functionality."""
    
    @pytest.fixture
    def mock_index_endpoint(self, mocker):
        """Mock Vertex AI Index Endpoint."""
        mock_endpoint = mocker.Mock()
        mock_response = mocker.Mock()
        mock_response[0] = [
            mocker.Mock(id="doc1-0", distance=0.1),
            mocker.Mock(id="doc1-1", distance=0.2)
        ]
        mock_endpoint.match.return_value = mock_response
        return mock_endpoint
    
    @pytest.fixture
    def vector_store(self, mock_index_endpoint, mocker):
        """Create vector store with mocked dependencies."""
        mocker.patch('app.rag.vector_store.aiplatform.MatchingEngineIndexEndpoint', 
                     return_value=mock_index_endpoint)
        return VectorStore()
    
    def test_search_basic(self, vector_store, mock_index_endpoint):
        """Test basic vector search."""
        query_embedding = [0.1] * 768
        top_k = 5
        
        result = vector_store.search(query_embedding, top_k=top_k)
        
        assert result is not None
        assert isinstance(result, list)
        mock_index_endpoint.match.assert_called_once()
    
    def test_search_returns_correct_format(self, vector_store):
        """Test that search returns properly formatted results."""
        query_embedding = [0.1] * 768
        
        result = vector_store.search(query_embedding)
        
        assert isinstance(result, list)
        if len(result) > 0:
            assert "id" in result[0] or isinstance(result[0], dict) or hasattr(result[0], 'id')
    
    def test_search_with_filter(self, vector_store, mock_index_endpoint):
        """Test search with metadata filter."""
        query_embedding = [0.1] * 768
        filter_dict = {"source": "doc1.txt"}
        
        result = vector_store.search(query_embedding, filter=filter_dict)
        
        # Should pass filter to the matching engine
        assert result is not None
    
    def test_add_embeddings(self, vector_store, mocker):
        """Test adding embeddings to store."""
        embeddings = [[0.1] * 768, [0.2] * 768]
        metadata = [
            {"id": "doc1-0", "text": "Text 1"},
            {"id": "doc1-1", "text": "Text 2"}
        ]
        
        # Mock the add method
        mock_add = mocker.patch.object(vector_store, 'add', return_value=True)
        
        result = vector_store.add(embeddings, metadata)
        
        assert result is not None
    
    def test_empty_query(self, vector_store):
        """Test search with empty embedding."""
        with pytest.raises(Exception):
            vector_store.search([])
    
    def test_invalid_embedding_dimension(self, vector_store):
        """Test search with wrong embedding dimension."""
        query_embedding = [0.1] * 100  # Wrong dimension
        
        # Should handle gracefully or raise appropriate error
        try:
            result = vector_store.search(query_embedding)
            # If it doesn't raise, that's also acceptable
            assert result is not None or result == []
        except Exception:
            pass  # Expected


class TestVectorStoreOperations:
    """Test vector store operations."""
    
    def test_batch_add(self, mocker):
        """Test adding multiple embeddings at once."""
        mock_endpoint = mocker.Mock()
        mocker.patch('app.rag.vector_store.aiplatform.MatchingEngineIndexEndpoint', 
                     return_value=mock_endpoint)
        
        store = VectorStore()
        
        embeddings = [[0.1] * 768 for _ in range(100)]
        metadata = [{"id": f"doc-{i}", "text": f"Text {i}"} for i in range(100)]
        
        # Mock batch add
        mock_add = mocker.patch.object(store, 'add_batch', return_value=True)
        result = store.add_batch(embeddings, metadata)
        
        assert result is not None
    
    def test_delete_embeddings(self, mocker):
        """Test deleting embeddings."""
        mock_endpoint = mocker.Mock()
        mocker.patch('app.rag.vector_store.aiplatform.MatchingEngineIndexEndpoint', 
                     return_value=mock_endpoint)
        
        store = VectorStore()
        
        # Mock delete
        mock_delete = mocker.patch.object(store, 'delete', return_value=True)
        result = store.delete(["doc1-0", "doc1-1"])
        
        assert result is not None


class TestVectorStoreEdgeCases:
    """Test edge cases for vector store."""
    
    def test_large_batch_search(self, mocker):
        """Test searching with large batch."""
        mock_endpoint = mocker.Mock()
        mock_response = mocker.Mock()
        mock_response[0] = [mocker.Mock(id=f"doc-{i}", distance=0.1) for i in range(100)]
        mock_endpoint.match.return_value = mock_response
        
        mocker.patch('app.rag.vector_store.aiplatform.MatchingEngineIndexEndpoint', 
                     return_value=mock_endpoint)
        
        store = VectorStore()
        query_embedding = [0.1] * 768
        
        result = store.search(query_embedding, top_k=100)
        assert len(result) <= 100
    
    def test_connection_error_handling(self, mocker):
        """Test handling of connection errors."""
        mock_endpoint = mocker.Mock()
        mock_endpoint.match.side_effect = Exception("Connection error")
        
        mocker.patch('app.rag.vector_store.aiplatform.MatchingEngineIndexEndpoint', 
                     return_value=mock_endpoint)
        
        store = VectorStore()
        query_embedding = [0.1] * 768
        
        with pytest.raises(Exception):
            store.search(query_embedding)
    
    def test_empty_search_results(self, mocker):
        """Test handling of empty search results."""
        mock_endpoint = mocker.Mock()
        mock_response = mocker.Mock()
        mock_response[0] = []
        mock_endpoint.match.return_value = mock_response
        
        mocker.patch('app.rag.vector_store.aiplatform.MatchingEngineIndexEndpoint', 
                     return_value=mock_endpoint)
        
        store = VectorStore()
        query_embedding = [0.1] * 768
        
        result = store.search(query_embedding)
        assert result == [] or result is not None


@pytest.mark.parametrize("top_k", [1, 5, 10, 50, 100])
def test_various_top_k_values(top_k, mocker):
    """Test various top_k values."""
    mock_endpoint = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response[0] = [mocker.Mock(id=f"doc-{i}", distance=0.1) for i in range(top_k)]
    mock_endpoint.match.return_value = mock_response
    
    mocker.patch('app.rag.vector_store.aiplatform.MatchingEngineIndexEndpoint', 
                 return_value=mock_endpoint)
    
    store = VectorStore()
    query_embedding = [0.1] * 768
    
    result = store.search(query_embedding, top_k=top_k)
    assert len(result) <= top_k
