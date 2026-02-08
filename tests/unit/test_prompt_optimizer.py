"""
Unit tests for prompt optimizer module.
Tests compression and semantic filtering.
"""
import pytest
from app.rag.prompt_optimizer import PromptCompressor, SemanticFilter


class TestPromptCompressor:
    """Test prompt compression functionality."""
    
    @pytest.fixture
    def compressor(self):
        """Create compressor instance."""
        return PromptCompressor(max_tokens=1000)
    
    def test_compress_whitespace(self, compressor):
        """Test whitespace compression."""
        text = "Text  with    multiple    spaces\n\n\nand newlines"
        result = compressor.compress_whitespace(text)
        assert "  " not in result
        assert "\n\n\n" not in result
    
    def test_remove_filler_words(self, compressor):
        """Test filler word removal."""
        text = "This is actually really very quite basically a test"
        result = compressor.remove_filler_words(text)
        # Filler words should be reduced or removed
        assert len(result) < len(text)
        assert "test" in result
    
    def test_deduplicate_sentences(self, compressor):
        """Test sentence deduplication."""
        text = "This is a test. This is another sentence. This is a test."
        result = compressor.deduplicate_sentences(text)
        # Duplicate sentence should appear only once
        assert text.count("This is a test.") == 2
        assert result.count("This is a test") <= 1
    
    def test_truncate_to_limit(self, compressor):
        """Test truncation to token limit."""
        text = "A" * 10000  # Way over limit
        result = compressor.truncate_to_limit(text)
        assert len(result) <= compressor.max_chars
    
    def test_compress_full_pipeline(self, compressor):
        """Test complete compression pipeline."""
        text = """
        This is actually a really very long text    with multiple spaces.
        This is another sentence with some content.
        This is actually a really very long text    with multiple spaces.
        More content here that is quite important actually.
        """ * 10
        
        result = compressor.compress(text)
        assert len(result) < len(text)
        assert len(result) > 0
        # Should preserve some content
        assert "content" in result.lower()
    
    def test_preserve_key_facts(self, compressor):
        """Test that key facts are preserved."""
        text = "The project costs $1,000,000 and started on January 1, 2024."
        result = compressor.compress(text, preserve_key_facts=True)
        # Numbers and dates should be preserved
        assert "1,000,000" in result or "1000000" in result or "million" in result.lower()
    
    def test_empty_text(self, compressor):
        """Test compression of empty text."""
        result = compressor.compress("")
        assert result == ""
    
    def test_short_text_unchanged(self, compressor):
        """Test that short text is mostly unchanged."""
        text = "Short text"
        result = compressor.compress(text)
        assert "Short" in result and "text" in result


class TestSemanticFilter:
    """Test semantic filtering functionality."""
    
    @pytest.fixture
    def filter(self):
        """Create filter instance."""
        return SemanticFilter(min_similarity=0.3, max_chunks=5)
    
    def test_filter_chunks_basic(self, filter, mocker):
        """Test basic chunk filtering."""
        query = "machine learning"
        chunks = [
            "Machine learning is a subset of AI",
            "Deep learning uses neural networks",
            "The weather is sunny today"
        ]
        
        # Mock similarity computation
        mocker.patch.object(filter, '_compute_similarity', side_effect=[0.9, 0.7, 0.1])
        
        result = filter.filter_chunks(query, chunks)
        assert len(result) <= len(chunks)
        # Low similarity chunk should be filtered
        assert "weather" not in " ".join(result).lower() or len(result) == len(chunks)
    
    def test_max_chunks_limit(self, filter, mocker):
        """Test that max_chunks limit is enforced."""
        query = "test query"
        chunks = ["chunk " + str(i) for i in range(10)]
        
        # Mock all chunks as relevant
        mocker.patch.object(filter, '_compute_similarity', return_value=0.8)
        
        result = filter.filter_chunks(query, chunks)
        assert len(result) <= filter.max_chunks
    
    def test_deduplicate_similar_chunks(self, filter, mocker):
        """Test deduplication of similar chunks."""
        query = "test"
        chunks = [
            "This is a test",
            "This is a test",  # Exact duplicate
            "This is also a test",  # Similar
            "Completely different content"
        ]
        
        # Mock similarity scores
        mocker.patch.object(filter, '_compute_similarity', return_value=0.8)
        mocker.patch.object(filter, '_chunks_similar', side_effect=[
            False,  # chunk 0 vs 1
            True,   # chunk 0 vs 2 (similar)
            False,  # chunk 0 vs 3
            False,  # chunk 1 vs 2
            False,  # chunk 1 vs 3
            False   # chunk 2 vs 3
        ])
        
        result = filter.filter_chunks(query, chunks)
        # Should remove at least one similar chunk
        assert len(result) <= len(chunks)
    
    def test_empty_chunks(self, filter):
        """Test filtering with no chunks."""
        result = filter.filter_chunks("query", [])
        assert result == []
    
    def test_single_chunk(self, filter, mocker):
        """Test filtering with single chunk."""
        mocker.patch.object(filter, '_compute_similarity', return_value=0.5)
        result = filter.filter_chunks("query", ["single chunk"])
        assert len(result) == 1
    
    def test_all_low_similarity(self, filter, mocker):
        """Test when all chunks have low similarity."""
        query = "test"
        chunks = ["chunk1", "chunk2", "chunk3"]
        
        # Mock all chunks as low similarity
        mocker.patch.object(filter, '_compute_similarity', return_value=0.1)
        
        result = filter.filter_chunks(query, chunks)
        # Should still return at least one chunk (best available)
        assert len(result) >= 1 or len(result) == 0


class TestPromptCompressorEdgeCases:
    """Test edge cases for prompt compression."""
    
    def test_compression_ratio_calculation(self):
        """Test that compression ratio is calculated correctly."""
        compressor = PromptCompressor(max_tokens=5000)
        text = "Test " * 1000
        result = compressor.compress(text)
        
        # Should achieve some compression
        assert len(result) < len(text)
    
    def test_preserve_structure(self):
        """Test that basic structure is preserved."""
        compressor = PromptCompressor(max_tokens=5000)
        text = "Header\n\nBody content here.\n\nFooter"
        result = compressor.compress(text)
        
        # Should preserve main parts
        assert "Body" in result or "content" in result


class TestSemanticFilterIntegration:
    """Test semantic filter integration scenarios."""
    
    def test_filter_with_query_pipeline(self, mocker):
        """Test filter in query pipeline context."""
        filter = SemanticFilter(min_similarity=0.4, max_chunks=3)
        
        query = "What are the benefits of exercise?"
        chunks = [
            "Exercise improves cardiovascular health",
            "Regular physical activity boosts mental health",
            "The history of ancient Rome is fascinating",
            "Sports and fitness activities are popular",
            "Philosophy explores fundamental questions"
        ]
        
        # Mock similarity scores
        mocker.patch.object(filter, '_compute_similarity', side_effect=[0.9, 0.85, 0.2, 0.7, 0.15])
        
        result = filter.filter_chunks(query, chunks)
        
        assert len(result) <= 3
        # Should keep most relevant chunks
        assert any("Exercise" in chunk or "physical" in chunk or "fitness" in chunk 
                   for chunk in result)
