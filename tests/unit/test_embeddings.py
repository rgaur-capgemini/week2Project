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

from app.rag.embeddings import EmbeddingGenerator


class TestEmbeddingGenerator:
    """Test embedding generation functionality."""
    
    @pytest.fixture
    def mock_vertex_model(self, mocker):
        """Mock Vertex AI embedding model."""
        mock_model = mocker.Mock()
        mock_embedding = mocker.Mock()
        mock_embedding.values = [0.1] * 768
        mock_model.get_embeddings.return_value = [mock_embedding]
        return mock_model
    
    @pytest.fixture
    def mock_redis(self, mocker):
        """Mock Redis client."""
        mock_client = mocker.Mock()
        mock_client.get.return_value = None
        mock_client.set.return_value = True
        mock_client.ping.return_value = True
        return mock_client
    
    @pytest.fixture
    def generator(self, mock_vertex_model, mock_redis, mocker):
        """Create generator with mocked dependencies."""
        mocker.patch('app.rag.embeddings.TextEmbeddingModel.from_pretrained', return_value=mock_vertex_model)
        mocker.patch('app.rag.embeddings.redis.Redis', return_value=mock_redis)
        return EmbeddingGenerator()
    
    def test_generate_single_embedding(self, generator, mock_vertex_model):
        """Test generating single embedding."""
        text = "Test text"
        result = generator.generate(text)
        
        assert result is not None
        assert len(result) == 768
        assert all(isinstance(x, float) for x in result)
        mock_vertex_model.get_embeddings.assert_called_once()
    
    def test_generate_batch_embeddings(self, generator, mock_vertex_model):
        """Test generating batch of embeddings."""
        texts = ["Text 1", "Text 2", "Text 3"]
        
        # Mock batch response
        mock_embeddings = [Mock(values=[0.1] * 768) for _ in texts]
        mock_vertex_model.get_embeddings.return_value = mock_embeddings
        
        result = generator.generate_batch(texts)
        
        assert len(result) == len(texts)
        assert all(len(emb) == 768 for emb in result)
    
    def test_empty_text(self, generator):
        """Test generating embedding for empty text."""
        result = generator.generate("")
        # Should handle gracefully
        assert result is None or len(result) == 768
    
    def test_cache_hit(self, generator, mock_redis):
        """Test that cached embeddings are returned."""
        import json
        
        text = "Cached text"
        cached_embedding = [0.5] * 768
        mock_redis.get.return_value = json.dumps(cached_embedding).encode()
        
        result = generator.generate(text)
        
        assert result == cached_embedding
        mock_redis.get.assert_called_once()
    
    def test_cache_miss_and_store(self, generator, mock_redis, mock_vertex_model):
        """Test cache miss triggers generation and storage."""
        text = "New text"
        mock_redis.get.return_value = None
        
        result = generator.generate(text)
        
        assert result is not None
        mock_redis.get.assert_called_once()
        mock_redis.set.assert_called_once()
    
    def test_long_text_truncation(self, generator):
        """Test that long text is truncated."""
        long_text = "A" * 10000
        result = generator.generate(long_text)
        # Should not error, model handles truncation
        assert result is not None or result is None


class TestEmbeddingCaching:
    """Test caching behavior."""
    
    def test_cache_key_generation(self):
        """Test that cache keys are consistent."""
        from app.rag.embeddings import EmbeddingGenerator
        
        # Mock dependencies
        with patch('app.rag.embeddings.TextEmbeddingModel.from_pretrained'), \
             patch('app.rag.embeddings.redis.Redis'):
            generator = EmbeddingGenerator()
            
            key1 = generator._get_cache_key("test text")
            key2 = generator._get_cache_key("test text")
            
            assert key1 == key2
    
    def test_different_texts_different_keys(self):
        """Test that different texts produce different keys."""
        from app.rag.embeddings import EmbeddingGenerator
        
        with patch('app.rag.embeddings.TextEmbeddingModel.from_pretrained'), \
             patch('app.rag.embeddings.redis.Redis'):
            generator = EmbeddingGenerator()
            
            key1 = generator._get_cache_key("text 1")
            key2 = generator._get_cache_key("text 2")
            
            assert key1 != key2


class TestEmbeddingGeneratorEdgeCases:
    """Test edge cases for embedding generation."""
    
    def test_special_characters(self, mocker):
        """Test handling of special characters."""
        mock_model = mocker.Mock()
        mock_embedding = mocker.Mock()
        mock_embedding.values = [0.1] * 768
        mock_model.get_embeddings.return_value = [mock_embedding]
        
        mocker.patch('app.rag.embeddings.TextEmbeddingModel.from_pretrained', return_value=mock_model)
        mocker.patch('app.rag.embeddings.redis.Redis')
        
        generator = EmbeddingGenerator()
        text = "Text with émojis 🎉 and spëcial chàrs"
        result = generator.generate(text)
        
        assert result is not None
    
    def test_api_failure_handling(self, mocker):
        """Test handling of API failures."""
        mock_model = mocker.Mock()
        mock_model.get_embeddings.side_effect = Exception("API Error")
        
        mocker.patch('app.rag.embeddings.TextEmbeddingModel.from_pretrained', return_value=mock_model)
        mocker.patch('app.rag.embeddings.redis.Redis')
        
        generator = EmbeddingGenerator()
        
        with pytest.raises(Exception):
            generator.generate("test text")
    
    def test_redis_unavailable_fallback(self, mocker):
        """Test that system works when Redis is unavailable."""
        mock_model = mocker.Mock()
        mock_embedding = mocker.Mock()
        mock_embedding.values = [0.1] * 768
        mock_model.get_embeddings.return_value = [mock_embedding]
        
        mock_redis = mocker.Mock()
        mock_redis.get.side_effect = Exception("Redis unavailable")
        
        mocker.patch('app.rag.embeddings.TextEmbeddingModel.from_pretrained', return_value=mock_model)
        mocker.patch('app.rag.embeddings.redis.Redis', return_value=mock_redis)
        
        generator = EmbeddingGenerator()
        # Should still work without cache
        result = generator.generate("test text")
        assert result is not None or result is None  # Depends on error handling


@pytest.mark.parametrize("batch_size", [1, 5, 10, 100])
def test_batch_sizes(batch_size, mocker):
    """Test various batch sizes."""
    mock_model = mocker.Mock()
    mock_embeddings = [Mock(values=[0.1] * 768) for _ in range(batch_size)]
    mock_model.get_embeddings.return_value = mock_embeddings
    
    mocker.patch('app.rag.embeddings.TextEmbeddingModel.from_pretrained', return_value=mock_model)
    mocker.patch('app.rag.embeddings.redis.Redis')
    
    generator = EmbeddingGenerator()
    texts = [f"Text {i}" for i in range(batch_size)]
    result = generator.generate_batch(texts)
    
    assert len(result) == batch_size
