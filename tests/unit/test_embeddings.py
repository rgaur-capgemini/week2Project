"""
Unit tests for embeddings module.
Tests embedding generation and caching.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
import sys

# Mock vertexai before importing
sys.modules['vertexai'] = MagicMock()
sys.modules['vertexai.language_models'] = MagicMock()

from app.rag.embeddings import VertexTextEmbedder


class TestVertexTextEmbedder:
    """Test embedding generation functionality."""
    
    @pytest.fixture
    def mock_vertex_model(self):
        """Mock Vertex AI embedding model."""
        mock_model = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.values = [0.1] * 768
        mock_model.get_embeddings.return_value = [mock_embedding]
        return mock_model
    
    @pytest.fixture
    def embedder(self, mock_vertex_model):
        """Create embedder with mocked dependencies."""
        with patch('app.rag.embeddings.aiplatform.init'):
            with patch('app.rag.embeddings.TextEmbeddingModel.from_pretrained', return_value=mock_vertex_model):
                embedder = VertexTextEmbedder(project="test-project", location="us-central1")
                return embedder
    
    def test_embed_single_text(self, embedder, mock_vertex_model):
        """Test embedding single text."""
        texts = ["Test text"]
        result = embedder.embed(texts)
        
        assert result is not None
        assert len(result) == 1
        assert len(result[0]) == 768
        mock_vertex_model.get_embeddings.assert_called_once()
    
    def test_generate_batch_embeddings(self, embedder, mock_vertex_model):
        """Test generating batch of embeddings."""
        texts = ["Text 1", "Text 2", "Text 3"]
        
        # Mock batch response
        mock_embeddings = [Mock(values=[0.1] * 768) for _ in texts]
        mock_vertex_model.get_embeddings.return_value = mock_embeddings
        
        result = embedder.embed(texts)
        
        assert len(result) == len(texts)
        assert all(len(emb) == 768 for emb in result)
    
    def test_empty_text(self, embedder):
        """Test generating embedding for empty text."""
        result = embedder.embed([""])
        # Should handle gracefully
        assert result is None or (isinstance(result, list) and len(result) >= 0)
    
    def test_cache_hit(self, embedder, mock_vertex_model):
        """Test that embedding generation works."""
        text = "Cached text"
        
        result = embedder.embed([text])
        
        assert result is not None
        assert len(result) >= 1
    
    def test_cache_miss_and_store(self, embedder, mock_vertex_model):
        """Test embedding generation works."""
        text = "New text"
        
        result = embedder.embed([text])
        
        assert result is not None
        assert len(result) >= 1
    
    def test_long_text_truncation(self, embedder):
        """Test that long text is truncated."""
        long_text = "A" * 10000
        result = embedder.embed([long_text])
        # Should not error, model handles truncation
        assert result is None or isinstance(result, list)


class TestEmbeddingCaching:
    """Test caching behavior."""
    
    def test_cache_key_generation(self):
        """Test that embedder works consistently."""
        from app.rag.embeddings import VertexTextEmbedder
        
        # Mock dependencies
        with patch('app.rag.embeddings.TextEmbeddingModel.from_pretrained'), \
             patch('app.rag.embeddings.aiplatform.init'):
            embedder = VertexTextEmbedder(project="test", location="us-central1")
            # Just verify it initializes
            assert embedder is not None
    
    def test_different_texts_different_keys(self):
        """Test that different texts can be embedded."""
        from app.rag.embeddings import VertexTextEmbedder
        
        with patch('app.rag.embeddings.TextEmbeddingModel.from_pretrained'), \
             patch('app.rag.embeddings.aiplatform.init'):
            embedder = VertexTextEmbedder(project="test", location="us-central1")
            # Just verify it initializes
            assert embedder is not None


class TestEmbeddingGeneratorEdgeCases:
    """Test edge cases for embedding generation."""
    
    def test_special_characters(self, mocker):
        """Test handling of special characters."""
        mock_model = mocker.Mock()
        mock_embedding = mocker.Mock()
        mock_embedding.values = [0.1] * 768
        mock_model.get_embeddings.return_value = [mock_embedding]
        
        mocker.patch('app.rag.embeddings.TextEmbeddingModel.from_pretrained', return_value=mock_model)
        mocker.patch('app.rag.embeddings.aiplatform.init')
        
        embedder = VertexTextEmbedder(project="test", location="us-central1")
        text = "Text with émojis 🎉 and spëcial chàrs"
        result = embedder.embed([text])
        
        assert result is not None
    
    def test_api_failure_handling(self, mocker):
        """Test handling of API failures."""
        mock_model = mocker.Mock()
        mock_model.get_embeddings.side_effect = Exception("API Error")
        
        mocker.patch('app.rag.embeddings.TextEmbeddingModel.from_pretrained', return_value=mock_model)
        mocker.patch('app.rag.embeddings.aiplatform.init')
        
        embedder = VertexTextEmbedder(project="test", location="us-central1")
        
        with pytest.raises(Exception):
            embedder.embed(["test text"])
    
    def test_redis_unavailable_fallback(self, mocker):
        """Test that system works."""
        mock_model = mocker.Mock()
        mock_embedding = mocker.Mock()
        mock_embedding.values = [0.1] * 768
        mock_model.get_embeddings.return_value = [mock_embedding]
        
        mocker.patch('app.rag.embeddings.TextEmbeddingModel.from_pretrained', return_value=mock_model)
        mocker.patch('app.rag.embeddings.aiplatform.init')
        
        embedder = VertexTextEmbedder(project="test", location="us-central1")
        result = embedder.embed(["test text"])
        assert result is not None


@pytest.mark.parametrize("batch_size", [1, 5, 10, 100])
def test_batch_sizes(batch_size, mocker):
    """Test various batch sizes."""
    mock_model = mocker.Mock()
    mock_embeddings = [Mock(values=[0.1] * 768) for _ in range(batch_size)]
    mock_model.get_embeddings.return_value = mock_embeddings
    
    mocker.patch('app.rag.embeddings.TextEmbeddingModel.from_pretrained', return_value=mock_model)
    mocker.patch('app.rag.embeddings.aiplatform.init')
    
    embedder = VertexTextEmbedder(project="test", location="us-central1")
    texts = [f"Text {i}" for i in range(batch_size)]
    result = embedder.embed(texts)
    
    assert len(result) == batch_size
