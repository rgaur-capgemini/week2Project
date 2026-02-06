"""
Test suite for prompt compression and semantic chunking.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import numpy as np
from app.rag.generator import GeminiGenerator
from app.rag.semantic_chunker import SemanticChunker, create_semantic_chunks


class TestPromptCompression:
    """Test prompt compression functionality."""
    
    @pytest.fixture
    def mock_embedder(self):
        """Create a mock embedder."""
        embedder = Mock()
        embedder.get_embeddings.return_value = [
            Mock(values=[0.1] * 768),
            Mock(values=[0.2] * 768),
            Mock(values=[0.3] * 768)
        ]
        return embedder
    
    @pytest.fixture
    def generator(self, mock_embedder):
        """Create GeminiGenerator with mocked dependencies."""
        with patch('app.rag.generator.vertexai.init'):
            with patch('app.rag.generator.GenerativeModel'):
                with patch('app.rag.generator.TextEmbeddingModel') as mock_embedding_model:
                    mock_embedding_model.from_pretrained.return_value = mock_embedder
                    gen = GeminiGenerator(project='test-project', location='us-central1')
                    gen.embedder = mock_embedder
                    return gen
    
    def test_compress_context_under_limit(self, generator):
        """Test compression when contexts are already under token limit."""
        contexts = ["Short context 1", "Short context 2"]
        query = "Test query"
        
        compressed = generator.compress_context(contexts, query, max_tokens=10000)
        
        # Should return unchanged if under limit
        assert len(compressed) == len(contexts)
    
    def test_compress_context_over_limit(self, generator):
        """Test compression when contexts exceed token limit."""
        # Create large contexts
        contexts = ["A" * 5000 for _ in range(10)]  # 50,000 chars total
        query = "Test query"
        
        compressed = generator.compress_context(contexts, query, max_tokens=1000)
        
        # Should compress to fit within limit
        total_chars = sum(len(ctx) for ctx in compressed)
        assert total_chars <= 1000 * 4  # 4 chars per token estimate
    
    def test_compress_context_empty(self, generator):
        """Test compression with empty contexts."""
        compressed = generator.compress_context([], "query", max_tokens=1000)
        assert compressed == []
    
    def test_compress_context_relevance_ranking(self, generator):
        """Test that compression ranks by relevance."""
        contexts = [
            "This is very relevant to the query",
            "This is somewhat relevant",
            "This is not relevant at all"
        ]
        query = "relevant query"
        
        # Mock embeddings to ensure first context is most similar
        def mock_embed(text):
            if "very relevant" in text:
                return np.array([1.0] * 768)
            elif "relevant query" in text:
                return np.array([0.9] * 768)
            else:
                return np.array([0.1] * 768)
        
        generator._embed = mock_embed
        
        compressed = generator.compress_context(contexts, query, max_tokens=500)
        
        # Most relevant context should be included
        assert any("very relevant" in ctx for ctx in compressed)


class TestSemanticChunking:
    """Test semantic chunking functionality."""
    
    @pytest.fixture
    def mock_embedder(self):
        """Create a mock embedder."""
        embedder = Mock()
        # Return different embeddings for different sentences
        embedder.get_embeddings.return_value = [
            Mock(values=np.random.rand(768).tolist()) for _ in range(5)
        ]
        return embedder
    
    @pytest.fixture
    def chunker(self, mock_embedder):
        """Create SemanticChunker with mocked embedder."""
        return SemanticChunker(
            embedder=mock_embedder,
            max_chunk_size=500,
            min_chunk_size=100,
            similarity_threshold=0.7
        )
    
    def test_chunk_simple_text(self, chunker):
        """Test chunking simple text."""
        text = "This is sentence one. This is sentence two. This is sentence three."
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
    
    def test_chunk_empty_text(self, chunker):
        """Test chunking empty text."""
        chunks = chunker.chunk_text("")
        assert chunks == []
    
    def test_chunk_respects_max_size(self, chunker):
        """Test that chunks don't exceed maximum size."""
        text = "A" * 10000  # Very long text
        chunks = chunker.chunk_text(text)
        
        for chunk in chunks:
            assert len(chunk) <= chunker.max_chunk_size
    
    def test_chunk_without_embedder(self):
        """Test fallback chunking without embedder."""
        chunker = SemanticChunker(embedder=None, max_chunk_size=500)
        text = "Sentence one. Sentence two. Sentence three."
        
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
    
    def test_create_semantic_chunks_convenience(self, mock_embedder):
        """Test convenience function."""
        text = "This is a test. Another sentence here."
        chunks = create_semantic_chunks(text, embedder=mock_embedder)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
    
    def test_sentence_splitting_spacy_fallback(self):
        """Test sentence splitting with and without spaCy."""
        chunker = SemanticChunker(embedder=None)
        text = "First sentence. Second sentence! Third sentence?"
        
        sentences = chunker._split_sentences(text)
        
        assert len(sentences) >= 3
        assert all(len(s) > 0 for s in sentences)
    
    def test_cosine_similarity(self, chunker):
        """Test cosine similarity calculation."""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        
        sim = chunker._cosine_similarity(vec1, vec2)
        
        assert 0.99 <= sim <= 1.01  # Should be very close to 1.0
    
    def test_cosine_similarity_zero_vectors(self, chunker):
        """Test cosine similarity with zero vectors."""
        vec1 = np.array([0.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        
        sim = chunker._cosine_similarity(vec1, vec2)
        
        assert sim == 0.0


class TestIntegration:
    """Integration tests for compression and chunking."""
    
    @pytest.fixture
    def mock_embedder(self):
        """Create a mock embedder."""
        embedder = Mock()
        embedder.get_embeddings.return_value = [
            Mock(values=np.random.rand(768).tolist())
        ]
        return embedder
    
    def test_end_to_end_chunking_and_compression(self, mock_embedder):
        """Test full pipeline from chunking to compression."""
        # Create long text
        text = "This is a document. " * 1000
        
        # Chunk it
        chunks = create_semantic_chunks(text, embedder=mock_embedder, max_chunk_size=1000)
        
        assert len(chunks) > 0
        
        # Compress chunks
        with patch('app.rag.generator.vertexai.init'):
            with patch('app.rag.generator.GenerativeModel'):
                with patch('app.rag.generator.TextEmbeddingModel') as mock_embedding_model:
                    mock_embedding_model.from_pretrained.return_value = mock_embedder
                    generator = GeminiGenerator(project='test', location='us-central1')
                    generator.embedder = mock_embedder
                    
                    compressed = generator.compress_context(
                        chunks, 
                        "document query", 
                        max_tokens=500
                    )
        
        assert len(compressed) <= len(chunks)
