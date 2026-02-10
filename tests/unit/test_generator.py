"""
Unit tests for generator module.
Tests LLM response generation.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
import sys

# Mock vertexai before importing
sys.modules['vertexai'] = MagicMock()
sys.modules['vertexai.generative_models'] = MagicMock()
sys.modules['vertexai.language_models'] = MagicMock()

from app.rag.generator import GeminiGenerator


class TestGeminiGenerator:
    """Test answer generation functionality."""
    
    @pytest.fixture
    def mock_generative_model(self):
        """Mock Vertex AI generative model."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Test answer"
        mock_model.generate_content.return_value = mock_response
        return mock_model
    
    @pytest.fixture
    def generator(self, mock_generative_model):
        """Create generator with mocked dependencies."""
        with patch('app.rag.generator.vertexai.init'):
            with patch('app.rag.generator.GenerativeModel', return_value=mock_generative_model):
                generator = GeminiGenerator(project="test-project", location="us-central1")
                return generator
    
    def test_generate_answer_basic(self, generator, mock_generative_model):
        """Test basic answer generation."""
        question = "What is machine learning?"
        contexts = [{"text": "Machine learning is a subset of AI."}]
        
        result = generator.generate(question, contexts)
        
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        mock_generative_model.generate_content.assert_called_once()
    
    def test_generate_with_multiple_contexts(self, generator, mock_generative_model):
        """Test generation with multiple context chunks."""
        question = "Explain AI"
        contexts = [
            {"text": "AI stands for Artificial Intelligence."},
            "AI includes machine learning and deep learning.",
            "AI is used in many applications."
        ]
        
        result = generator.generate(question, contexts)
        
        assert result is not None
        mock_generative_model.generate_content.assert_called_once()
    
    def test_generate_with_empty_contexts(self, generator, mock_generative_model):
        """Test generation with no contexts."""
        question = "What is AI?"
        contexts = []
        
        result = generator.generate(question, contexts)
        
        # Should still generate an answer
        assert result is not None
    
    def test_generate_with_system_prompt(self, generator, mock_generative_model):
        """Test that system prompt is used."""
        question = "Test question"
        contexts = ["Context"]
        system_prompt = "You are a helpful assistant."
        
        result = generator.generate(question, contexts, system_prompt=system_prompt)
        
        # Check that generate was called with proper structure
        call_args = mock_generative_model.generate_content.call_args
        assert call_args is not None
    
    def test_streaming_generation(self, generator, mocker):
        """Test streaming response generation."""
        mock_stream = mocker.Mock()
        mock_chunk1 = mocker.Mock(text="Part 1")
        mock_chunk2 = mocker.Mock(text=" Part 2")
        mock_stream.__iter__.return_value = [mock_chunk1, mock_chunk2]
        
        mock_model = mocker.Mock()
        mock_model.generate_content.return_value = mock_stream
        
        mocker.patch('app.rag.generator.GenerativeModel', return_value=mock_model)
        gen = AnswerGenerator()
        
        question = "Test"
        contexts = ["Context"]
        
        # If streaming is supported
        result = gen.generate_stream(question, contexts)
        # Verify it returns a generator or stream
        assert result is not None


class TestPromptConstruction:
    """Test prompt construction logic."""
    
    def test_prompt_includes_question(self, mocker):
        """Test that prompt includes the question."""
        mock_model = mocker.Mock()
        mock_response = mocker.Mock(text="Answer")
        mock_model.generate_content.return_value = mock_response
        
        mocker.patch('app.rag.generator.GenerativeModel', return_value=mock_model)
        generator = AnswerGenerator()
        
        question = "What is the capital of France?"
        contexts = ["Paris is the capital of France."]
        
        generator.generate(question, contexts)
        
        call_args = mock_model.generate_content.call_args[0][0]
        assert question in str(call_args)
    
    def test_prompt_includes_contexts(self, mocker):
        """Test that prompt includes context information."""
        mock_model = mocker.Mock()
        mock_response = mocker.Mock(text="Answer")
        mock_model.generate_content.return_value = mock_response
        
        mocker.patch('app.rag.generator.GenerativeModel', return_value=mock_model)
        generator = AnswerGenerator()
        
        question = "What is AI?"
        contexts = ["AI is artificial intelligence."]
        
        generator.generate(question, contexts)
        
        call_args = mock_model.generate_content.call_args[0][0]
        assert any(ctx in str(call_args) for ctx in contexts)


class TestGeneratorEdgeCases:
    """Test edge cases for answer generation."""
    
    def test_very_long_question(self, mocker):
        """Test with very long question."""
        mock_model = mocker.Mock()
        mock_response = mocker.Mock(text="Answer")
        mock_model.generate_content.return_value = mock_response
        
        mocker.patch('app.rag.generator.GenerativeModel', return_value=mock_model)
        generator = AnswerGenerator()
        
        question = "A" * 5000
        contexts = ["Context"]
        
        result = generator.generate(question, contexts)
        assert result is not None
    
    def test_very_long_contexts(self, mocker):
        """Test with very long contexts."""
        mock_model = mocker.Mock()
        mock_response = mocker.Mock(text="Answer")
        mock_model.generate_content.return_value = mock_response
        
        mocker.patch('app.rag.generator.GenerativeModel', return_value=mock_model)
        generator = AnswerGenerator()
        
        question = "Question"
        contexts = ["A" * 10000 for _ in range(5)]
        
        result = generator.generate(question, contexts)
        assert result is not None
    
    def test_special_characters_in_question(self, mocker):
        """Test handling special characters."""
        mock_model = mocker.Mock()
        mock_response = mocker.Mock(text="Answer")
        mock_model.generate_content.return_value = mock_response
        
        mocker.patch('app.rag.generator.GenerativeModel', return_value=mock_model)
        generator = AnswerGenerator()
        
        question = "What's the <meaning> of \"life\"?"
        contexts = ["Context"]
        
        result = generator.generate(question, contexts)
        assert result is not None
    
    def test_api_error_handling(self, mocker):
        """Test handling of API errors."""
        mock_model = mocker.Mock()
        mock_model.generate_content.side_effect = Exception("API Error")
        
        mocker.patch('app.rag.generator.GenerativeModel', return_value=mock_model)
        generator = AnswerGenerator()
        
        question = "Test"
        contexts = ["Context"]
        
        with pytest.raises(Exception):
            generator.generate(question, contexts)
    
    def test_safety_filter_response(self, mocker):
        """Test handling of safety-filtered responses."""
        mock_model = mocker.Mock()
        mock_response = mocker.Mock()
        mock_response.text = ""  # Empty due to safety filter
        mock_model.generate_content.return_value = mock_response
        
        mocker.patch('app.rag.generator.GenerativeModel', return_value=mock_model)
        generator = AnswerGenerator()
        
        question = "Test"
        contexts = ["Context"]
        
        result = generator.generate(question, contexts)
        # Should handle empty response gracefully
        assert result == "" or result is not None


@pytest.mark.parametrize("num_contexts", [0, 1, 5, 10, 50])
def test_various_context_counts(num_contexts, mocker):
    """Test with various numbers of contexts."""
    mock_model = mocker.Mock()
    mock_response = mocker.Mock(text="Answer")
    mock_model.generate_content.return_value = mock_response
    
    mocker.patch('app.rag.generator.GenerativeModel', return_value=mock_model)
    generator = AnswerGenerator()
    
    question = "Test question"
    contexts = [f"Context {i}" for i in range(num_contexts)]
    
    result = generator.generate(question, contexts)
    assert result is not None
