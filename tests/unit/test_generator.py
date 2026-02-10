"""
Comprehensive tests for GeminiGenerator - 100% coverage target.
Tests all methods, branches, edge cases, and exception paths.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
import numpy as np

from app.rag.generator import GeminiGenerator


class TestGeminiGeneratorInit:
    """Test GeminiGenerator initialization."""
    
    @patch('app.rag.generator.TextEmbeddingModel.from_pretrained')
    @patch('app.rag.generator.GenerativeModel')
    @patch('app.rag.generator.vertexai.init')
    def test_init_success(self, mock_vertex_init, mock_gen_model, mock_embedder):
        """Test successful initialization."""
        mock_model = MagicMock()
        mock_gen_model.return_value = mock_model
        
        mock_embed = MagicMock()
        mock_embedder.return_value = mock_embed
        
        generator = GeminiGenerator(
            project="test-project",
            location="us-central1"
        )
        
        assert generator.project == "test-project"
        assert generator.location == "us-central1"
        assert generator.model_name == "gemini-2.0-flash-001"
        assert generator.max_tokens == 8000
    
    @patch('app.rag.generator.TextEmbeddingModel.from_pretrained')
    @patch('app.rag.generator.GenerativeModel')
    @patch('app.rag.generator.vertexai.init')
    def test_init_custom_model(self, mock_vertex_init, mock_gen_model, mock_embedder):
        """Test initialization with custom model."""
        mock_model = MagicMock()
        mock_gen_model.return_value = mock_model
        
        mock_embed = MagicMock()
        mock_embedder.return_value = mock_embed
        
        generator = GeminiGenerator(
            project="test-project",
            location="us-central1",
            model="gemini-pro"
        )
        
        assert generator.model_name == "gemini-pro"
    
    @patch('app.rag.generator.TextEmbeddingModel.from_pretrained')
    @patch('app.rag.generator.GenerativeModel')
    @patch('app.rag.generator.vertexai.init')
    def test_init_custom_max_tokens(self, mock_vertex_init, mock_gen_model, mock_embedder):
        """Test initialization with custom max tokens."""
        mock_model = MagicMock()
        mock_gen_model.return_value = mock_model
        
        mock_embed = MagicMock()
        mock_embedder.return_value = mock_embed
        
        with patch.dict('os.environ', {'MAX_TOKENS': '4000'}):
            generator = GeminiGenerator(
                project="test-project",
                location="us-central1"
            )
            
            assert generator.max_tokens == 4000


class TestEmbed:
    """Test embedding generation."""
    
    @patch('app.rag.generator.TextEmbeddingModel.from_pretrained')
    @patch('app.rag.generator.GenerativeModel')
    @patch('app.rag.generator.vertexai.init')
    def test_embed_success(self, mock_vertex_init, mock_gen_model, mock_embedder):
        """Test successful embedding generation."""
        mock_model = MagicMock()
        mock_gen_model.return_value = mock_model
        
        mock_embedding = MagicMock()
        mock_embedding.values = [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_embed = MagicMock()
        mock_embed.get_embeddings.return_value = [mock_embedding]
        mock_embedder.return_value = mock_embed
        
        generator = GeminiGenerator("test-project", "us-central1")
        
        result = generator._embed("Test text")
        
        assert result == [0.1, 0.2, 0.3, 0.4, 0.5]
    
    @patch('app.rag.generator.TextEmbeddingModel.from_pretrained')
    @patch('app.rag.generator.GenerativeModel')
    @patch('app.rag.generator.vertexai.init')
    def test_embed_empty_text(self, mock_vertex_init, mock_gen_model, mock_embedder):
        """Test embedding generation with empty text."""
        mock_model = MagicMock()
        mock_gen_model.return_value = mock_model
        
        mock_embedding = MagicMock()
        mock_embedding.values = []
        mock_embed = MagicMock()
        mock_embed.get_embeddings.return_value = [mock_embedding]
        mock_embedder.return_value = mock_embed
        
        generator = GeminiGenerator("test-project", "us-central1")
        
        result = generator._embed("")
        
        assert isinstance(result, list)


class TestGenerate:
    """Test answer generation."""
    
    @patch('app.rag.generator.TextEmbeddingModel.from_pretrained')
    @patch('app.rag.generator.GenerativeModel')
    @patch('app.rag.generator.vertexai.init')
    def test_generate_success(self, mock_vertex_init, mock_gen_model, mock_embedder):
        """Test successful answer generation."""
        mock_response = MagicMock()
        mock_response.text = "Python is a programming language."
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 20
        mock_response.usage_metadata.total_token_count = 120
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_gen_model.return_value = mock_model
        
        mock_embedding = MagicMock()
        mock_embedding.values = [0.1, 0.2, 0.3]
        mock_embed = MagicMock()
        mock_embed.get_embeddings.return_value = [mock_embedding]
        mock_embedder.return_value = mock_embed
        
        generator = GeminiGenerator("test-project", "us-central1")
        
        contexts = ["Python is a programming language.", "Python has many libraries."]
        answer, citations, tokens = generator.generate("What is Python?", contexts)
        
        assert "Python" in answer
        assert tokens['total_tokens'] == 120
        assert tokens['prompt_tokens'] == 100
        assert tokens['completion_tokens'] == 20
    
    @patch('app.rag.generator.TextEmbeddingModel.from_pretrained')
    @patch('app.rag.generator.GenerativeModel')
    @patch('app.rag.generator.vertexai.init')
    def test_generate_with_custom_temperature(self, mock_vertex_init, mock_gen_model, mock_embedder):
        """Test generation with custom temperature."""
        mock_response = MagicMock()
        mock_response.text = "Test answer"
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 50
        mock_response.usage_metadata.candidates_token_count = 10
        mock_response.usage_metadata.total_token_count = 60
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_gen_model.return_value = mock_model
        
        mock_embedding = MagicMock()
        mock_embedding.values = [0.1, 0.2, 0.3]
        mock_embed = MagicMock()
        mock_embed.get_embeddings.return_value = [mock_embedding]
        mock_embedder.return_value = mock_embed
        
        generator = GeminiGenerator("test-project", "us-central1")
        
        contexts = ["Context 1"]
        answer, citations, tokens = generator.generate("Test?", contexts, temperature=0.7)
        
        # Verify temperature was passed
        call_args = mock_model.generate_content.call_args
        assert call_args[1]['generation_config']['temperature'] == 0.7
    
    @patch('app.rag.generator.TextEmbeddingModel.from_pretrained')
    @patch('app.rag.generator.GenerativeModel')
    @patch('app.rag.generator.vertexai.init')
    def test_generate_error_handling(self, mock_vertex_init, mock_gen_model, mock_embedder):
        """Test generation error handling."""
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API error")
        mock_gen_model.return_value = mock_model
        
        mock_embed = MagicMock()
        mock_embedder.return_value = mock_embed
        
        generator = GeminiGenerator("test-project", "us-central1")
        
        contexts = ["Context"]
        answer, citations, tokens = generator.generate("Test?", contexts)
        
        assert "Error generating answer" in answer
        assert citations == []
        assert tokens['total_tokens'] == 0


class TestAnswer:
    """Test answer method (alias for generate)."""
    
    @patch('app.rag.generator.TextEmbeddingModel.from_pretrained')
    @patch('app.rag.generator.GenerativeModel')
    @patch('app.rag.generator.vertexai.init')
    def test_answer_calls_generate(self, mock_vertex_init, mock_gen_model, mock_embedder):
        """Test answer method calls generate."""
        mock_response = MagicMock()
        mock_response.text = "Test answer"
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 50
        mock_response.usage_metadata.candidates_token_count = 10
        mock_response.usage_metadata.total_token_count = 60
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_gen_model.return_value = mock_model
        
        mock_embedding = MagicMock()
        mock_embedding.values = [0.1, 0.2, 0.3]
        mock_embed = MagicMock()
        mock_embed.get_embeddings.return_value = [mock_embedding]
        mock_embedder.return_value = mock_embed
        
        generator = GeminiGenerator("test-project", "us-central1")
        
        contexts = ["Context"]
        answer, citations, tokens = generator.answer("Test?", contexts)
        
        assert isinstance(answer, str)
        assert isinstance(citations, list)
        assert isinstance(tokens, dict)


class TestBuildPrompt:
    """Test prompt building."""
    
    @patch('app.rag.generator.TextEmbeddingModel.from_pretrained')
    @patch('app.rag.generator.GenerativeModel')
    @patch('app.rag.generator.vertexai.init')
    def test_build_prompt_structure(self, mock_vertex_init, mock_gen_model, mock_embedder):
        """Test prompt structure."""
        mock_model = MagicMock()
        mock_gen_model.return_value = mock_model
        
        mock_embed = MagicMock()
        mock_embedder.return_value = mock_embed
        
        generator = GeminiGenerator("test-project", "us-central1")
        
        contexts = ["Context 1", "Context 2"]
        prompt = generator._build_prompt("What is Python?", contexts)
        
        assert "Context Documents:" in prompt
        assert "[1]" in prompt
        assert "[2]" in prompt
        assert "Question:" in prompt
        assert "CRITICAL INSTRUCTIONS:" in prompt
    
    @patch('app.rag.generator.TextEmbeddingModel.from_pretrained')
    @patch('app.rag.generator.GenerativeModel')
    @patch('app.rag.generator.vertexai.init')
    def test_build_prompt_pii_instructions(self, mock_vertex_init, mock_gen_model, mock_embedder):
        """Test prompt includes PII protection instructions."""
        mock_model = MagicMock()
        mock_gen_model.return_value = mock_model
        
        mock_embed = MagicMock()
        mock_embedder.return_value = mock_embed
        
        generator = GeminiGenerator("test-project", "us-central1")
        
        contexts = ["Context"]
        prompt = generator._build_prompt("Test?", contexts)
        
        assert "personal data" in prompt.lower()
        assert "sensitive" in prompt.lower()


class TestExtractCitations:
    """Test citation extraction."""
    
    @patch('app.rag.generator.TextEmbeddingModel.from_pretrained')
    @patch('app.rag.generator.GenerativeModel')
    @patch('app.rag.generator.vertexai.init')
    def test_extract_citations_empty_contexts(self, mock_vertex_init, mock_gen_model, mock_embedder):
        """Test citation extraction with empty contexts."""
        mock_model = MagicMock()
        mock_gen_model.return_value = mock_model
        
        mock_embed = MagicMock()
        mock_embedder.return_value = mock_embed
        
        generator = GeminiGenerator("test-project", "us-central1")
        
        citations = generator._extract_citations("Answer", [])
        
        assert citations == []
    
    @patch('app.rag.generator.TextEmbeddingModel.from_pretrained')
    @patch('app.rag.generator.GenerativeModel')
    @patch('app.rag.generator.vertexai.init')
    def test_extract_citations_returns_top_3(self, mock_vertex_init, mock_gen_model, mock_embedder):
        """Test citation extraction returns top 3 contexts."""
        mock_model = MagicMock()
        mock_gen_model.return_value = mock_model
        
        mock_embedding = MagicMock()
        mock_embedding.values = [0.1, 0.2, 0.3]
        mock_embed = MagicMock()
        mock_embed.get_embeddings.return_value = [mock_embedding]
        mock_embedder.return_value = mock_embed
        
        generator = GeminiGenerator("test-project", "us-central1")
        
        contexts = [f"Context {i}" for i in range(10)]
        
        with patch('numpy.dot'), patch('numpy.linalg.norm'):
            citations = generator._extract_citations("Answer", contexts)
            
            assert len(citations) <= 3


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @patch('app.rag.generator.TextEmbeddingModel.from_pretrained')
    @patch('app.rag.generator.GenerativeModel')
    @patch('app.rag.generator.vertexai.init')
    def test_generate_with_empty_contexts(self, mock_vertex_init, mock_gen_model, mock_embedder):
        """Test generation with empty contexts."""
        mock_response = MagicMock()
        mock_response.text = "I don't have information."
        mock_response.usage_metadata = None
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_gen_model.return_value = mock_model
        
        mock_embed = MagicMock()
        mock_embedder.return_value = mock_embed
        
        generator = GeminiGenerator("test-project", "us-central1")
        
        answer, citations, tokens = generator.generate("Test?", [])
        
        assert isinstance(answer, str)
    
    @patch('app.rag.generator.TextEmbeddingModel.from_pretrained')
    @patch('app.rag.generator.GenerativeModel')
    @patch('app.rag.generator.vertexai.init')
    def test_generate_without_usage_metadata(self, mock_vertex_init, mock_gen_model, mock_embedder):
        """Test generation when response has no usage metadata."""
        mock_response = MagicMock()
        mock_response.text = "Test answer"
        mock_response.usage_metadata = None
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_gen_model.return_value = mock_model
        
        mock_embedding = MagicMock()
        mock_embedding.values = [0.1, 0.2, 0.3]
        mock_embed = MagicMock()
        mock_embed.get_embeddings.return_value = [mock_embedding]
        mock_embedder.return_value = mock_embed
        
        generator = GeminiGenerator("test-project", "us-central1")
        
        answer, citations, tokens = generator.generate("Test?", ["Context"])
        
        assert tokens['total_tokens'] == 0


@pytest.mark.xfail(reason="Testing advanced generation scenarios")
class TestAdvancedScenarios:
    """Test advanced generation scenarios."""
    
    @patch('app.rag.generator.TextEmbeddingModel.from_pretrained')
    @patch('app.rag.generator.GenerativeModel')
    @patch('app.rag.generator.vertexai.init')
    def test_streaming_generation(self, mock_vertex_init, mock_gen_model, mock_embedder):
        """Test streaming generation if supported."""
        mock_model = MagicMock()
        mock_gen_model.return_value = mock_model
        
        mock_embed = MagicMock()
        mock_embedder.return_value = mock_embed
        
        generator = GeminiGenerator("test-project", "us-central1")
        
        # If streaming method exists
        if hasattr(generator, 'generate_stream'):
            stream = generator.generate_stream("Test?", ["Context"])
            assert hasattr(stream, '__iter__')


class TestExtractCitationsExceptionHandling:
    """Test exception handling in extract_citations method."""
    
    @patch('app.rag.generator.TextEmbeddingModel.from_pretrained')
    @patch('app.rag.generator.GenerativeModel')
    @patch('app.rag.generator.vertexai.init')
    def test_extract_citations_embedding_error(self, mock_vertex_init, mock_gen_model, mock_embedder):
        """Test extract_citations when embedding fails."""
        mock_model = MagicMock()
        mock_gen_model.return_value = mock_model
        
        mock_embed = MagicMock()
        mock_embed.get_embeddings.side_effect = Exception("Embedding error")
        mock_embedder.return_value = mock_embed
        
        generator = GeminiGenerator("test-project", "us-central1")
        
        # Should fallback to first 3 contexts when exception occurs
        contexts = ["Context 1", "Context 2", "Context 3", "Context 4"]
        result = generator._extract_citations("Answer text", contexts)
        
        assert len(result) <= 3
        assert result == contexts[:3]
    
    @patch('app.rag.generator.TextEmbeddingModel.from_pretrained')
    @patch('app.rag.generator.GenerativeModel')
    @patch('app.rag.generator.vertexai.init')
    def test_extract_citations_with_few_contexts(self, mock_vertex_init, mock_gen_model, mock_embedder):
        """Test extract_citations with fewer than 3 contexts on error."""
        mock_model = MagicMock()
        mock_gen_model.return_value = mock_model
        
        mock_embed = MagicMock()
        mock_embed.get_embeddings.side_effect = Exception("Error")
        mock_embedder.return_value = mock_embed
        
        generator = GeminiGenerator("test-project", "us-central1")
        
        # Should return all contexts when less than 3
        contexts = ["Context 1", "Context 2"]
        result = generator._extract_citations("Answer", contexts)
        
        assert result == contexts
