"""
Comprehensive tests for RAGAS Evaluator - 100% coverage target.
Tests all methods, branches, edge cases, and exception paths.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
import numpy as np

from app.rag.ragas_eval import RAGASMetrics, RAGASEvaluator


class TestRAGASMetrics:
    """Test RAGASMetrics dataclass."""
    
    def test_metrics_creation(self):
        """Test creating metrics instance."""
        metrics = RAGASMetrics(
            answer_correctness=0.8,
            faithfulness=0.9,
            context_precision=0.7,
            context_recall=0.85,
            toxicity_score=0.1
        )
        
        assert metrics.answer_correctness == 0.8
        assert metrics.faithfulness == 0.9
        assert metrics.context_precision == 0.7
        assert metrics.context_recall == 0.85
        assert metrics.toxicity_score == 0.1
    
    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = RAGASMetrics(
            answer_correctness=0.8,
            faithfulness=0.9,
            context_precision=0.7,
            context_recall=0.85,
            toxicity_score=0.1
        )
        
        result = metrics.to_dict()
        
        assert result["answer_correctness"] == 0.8
        assert result["faithfulness"] == 0.9
        assert "overall_score" in result
    
    def test_overall_score_calculation(self):
        """Test overall score calculation."""
        metrics = RAGASMetrics(
            answer_correctness=0.8,
            faithfulness=0.9,
            context_precision=0.7,
            context_recall=0.85,
            toxicity_score=0.1
        )
        
        overall = metrics.overall_score()
        
        # Check weighted calculation
        expected = (0.3 * 0.8) + (0.3 * 0.9) + (0.2 * 0.7) + (0.1 * 0.85) + (0.1 * 0.9)
        assert abs(overall - expected) < 0.01
    
    def test_overall_score_with_zeros(self):
        """Test overall score with zero values."""
        metrics = RAGASMetrics(
            answer_correctness=0.0,
            faithfulness=0.0,
            context_precision=0.0,
            context_recall=0.0,
            toxicity_score=0.0
        )
        
        overall = metrics.overall_score()
        assert overall >= 0.0
    
    def test_overall_score_perfect(self):
        """Test overall score with perfect values."""
        metrics = RAGASMetrics(
            answer_correctness=1.0,
            faithfulness=1.0,
            context_precision=1.0,
            context_recall=1.0,
            toxicity_score=0.0
        )
        
        overall = metrics.overall_score()
        assert overall == 1.0


class TestRAGASEvaluatorInit:
    """Test RAGASEvaluator initialization."""
    
    @patch('app.rag.ragas_eval.aiplatform.init')
    @patch('app.rag.ragas_eval.GenerativeModel')
    @patch('app.rag.ragas_eval.TextEmbeddingModel')
    def test_init_default_model(self, mock_embed, mock_gen, mock_init):
        """Test initialization with default model."""
        mock_embed.from_pretrained.return_value = MagicMock()
        
        evaluator = RAGASEvaluator(project="test-project", location="us-central1")
        
        mock_init.assert_called_once_with(project="test-project", location="us-central1")
        assert evaluator.llm is not None
        assert evaluator.embedder is not None
    
    @patch('app.rag.ragas_eval.aiplatform.init')
    @patch('app.rag.ragas_eval.GenerativeModel')
    @patch('app.rag.ragas_eval.TextEmbeddingModel')
    def test_init_custom_model(self, mock_embed, mock_gen, mock_init):
        """Test initialization with custom model."""
        mock_embed.from_pretrained.return_value = MagicMock()
        
        evaluator = RAGASEvaluator(
            project="test-project",
            location="us-central1",
            model="gemini-1.5-pro"
        )
        
        assert evaluator.llm is not None


class TestEvaluate:
    """Test evaluate method."""
    
    @patch('app.rag.ragas_eval.aiplatform.init')
    @patch('app.rag.ragas_eval.GenerativeModel')
    @patch('app.rag.ragas_eval.TextEmbeddingModel')
    def test_evaluate_basic(self, mock_embed, mock_gen, mock_init):
        """Test basic evaluation."""
        mock_embed_instance = MagicMock()
        mock_embed_instance.get_embeddings.return_value = [MagicMock(values=[0.5] * 768)]
        mock_embed.from_pretrained.return_value = mock_embed_instance
        
        mock_gen_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "8"
        mock_gen_instance.generate_content.return_value = mock_response
        mock_gen.return_value = mock_gen_instance
        
        evaluator = RAGASEvaluator(project="test-project", location="us-central1")
        
        result = evaluator.evaluate(
            question="What is Python?",
            answer="Python is a programming language",
            contexts=["Python is a high-level programming language"],
            ground_truth="Python is a programming language"
        )
        
        assert isinstance(result, RAGASMetrics)
        assert 0 <= result.answer_correctness <= 1
        assert 0 <= result.faithfulness <= 1
    
    @patch('app.rag.ragas_eval.aiplatform.init')
    @patch('app.rag.ragas_eval.GenerativeModel')
    @patch('app.rag.ragas_eval.TextEmbeddingModel')
    def test_evaluate_without_ground_truth(self, mock_embed, mock_gen, mock_init):
        """Test evaluation without ground truth."""
        mock_embed_instance = MagicMock()
        mock_embed_instance.get_embeddings.return_value = [MagicMock(values=[0.5] * 768)]
        mock_embed.from_pretrained.return_value = mock_embed_instance
        
        mock_gen_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "7"
        mock_gen_instance.generate_content.return_value = mock_response
        mock_gen.return_value = mock_gen_instance
        
        evaluator = RAGASEvaluator(project="test-project", location="us-central1")
        
        result = evaluator.evaluate(
            question="What is Python?",
            answer="Python is a programming language",
            contexts=["Python is a programming language"],
            ground_truth=None
        )
        
        assert isinstance(result, RAGASMetrics)


class TestAnswerCorrectness:
    """Test _answer_correctness method."""
    
    @patch('app.rag.ragas_eval.aiplatform.init')
    @patch('app.rag.ragas_eval.GenerativeModel')
    @patch('app.rag.ragas_eval.TextEmbeddingModel')
    def test_answer_correctness_with_ground_truth(self, mock_embed, mock_gen, mock_init):
        """Test answer correctness with ground truth."""
        mock_embed_instance = MagicMock()
        mock_embed_instance.get_embeddings.return_value = [MagicMock(values=[0.8] * 768)]
        mock_embed.from_pretrained.return_value = mock_embed_instance
        
        evaluator = RAGASEvaluator(project="test-project", location="us-central1")
        
        score = evaluator._answer_correctness(
            question="What is 2+2?",
            answer="4",
            ground_truth="4"
        )
        
        assert 0 <= score <= 1
    
    @patch('app.rag.ragas_eval.aiplatform.init')
    @patch('app.rag.ragas_eval.GenerativeModel')
    @patch('app.rag.ragas_eval.TextEmbeddingModel')
    def test_answer_correctness_without_ground_truth(self, mock_embed, mock_gen, mock_init):
        """Test answer correctness without ground truth."""
        mock_embed_instance = MagicMock()
        mock_embed_instance.get_embeddings.return_value = [MagicMock(values=[0.8] * 768)]
        mock_embed.from_pretrained.return_value = mock_embed_instance
        
        evaluator = RAGASEvaluator(project="test-project", location="us-central1")
        
        score = evaluator._answer_correctness(
            question="What is Python?",
            answer="A programming language",
            ground_truth=None
        )
        
        assert 0 <= score <= 1


class TestFaithfulness:
    """Test _faithfulness method."""
    
    @patch('app.rag.ragas_eval.aiplatform.init')
    @patch('app.rag.ragas_eval.GenerativeModel')
    @patch('app.rag.ragas_eval.TextEmbeddingModel')
    def test_faithfulness_basic(self, mock_embed, mock_gen, mock_init):
        """Test faithfulness calculation."""
        mock_embed.from_pretrained.return_value = MagicMock()
        
        mock_gen_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "9"
        mock_gen_instance.generate_content.return_value = mock_response
        mock_gen.return_value = mock_gen_instance
        
        evaluator = RAGASEvaluator(project="test-project", location="us-central1")
        
        score = evaluator._faithfulness(
            answer="Python is great",
            contexts=["Python is a great programming language"]
        )
        
        assert 0 <= score <= 1
    
    @patch('app.rag.ragas_eval.aiplatform.init')
    @patch('app.rag.ragas_eval.GenerativeModel')
    @patch('app.rag.ragas_eval.TextEmbeddingModel')
    def test_faithfulness_empty_contexts(self, mock_embed, mock_gen, mock_init):
        """Test faithfulness with empty contexts."""
        mock_embed.from_pretrained.return_value = MagicMock()
        mock_gen.return_value = MagicMock()
        
        evaluator = RAGASEvaluator(project="test-project", location="us-central1")
        
        score = evaluator._faithfulness(answer="Test", contexts=[])
        
        assert score == 0.0


class TestContextPrecision:
    """Test _context_precision method."""
    
    @patch('app.rag.ragas_eval.aiplatform.init')
    @patch('app.rag.ragas_eval.GenerativeModel')
    @patch('app.rag.ragas_eval.TextEmbeddingModel')
    def test_context_precision_basic(self, mock_embed, mock_gen, mock_init):
        """Test context precision calculation."""
        mock_embed_instance = MagicMock()
        mock_embed_instance.get_embeddings.return_value = [MagicMock(values=[0.7] * 768)]
        mock_embed.from_pretrained.return_value = mock_embed_instance
        mock_gen.return_value = MagicMock()
        
        evaluator = RAGASEvaluator(project="test-project", location="us-central1")
        
        score = evaluator._context_precision(
            question="What is Python?",
            contexts=["Python is a language", "Java is also a language"]
        )
        
        assert 0 <= score <= 1
    
    @patch('app.rag.ragas_eval.aiplatform.init')
    @patch('app.rag.ragas_eval.GenerativeModel')
    @patch('app.rag.ragas_eval.TextEmbeddingModel')
    def test_context_precision_empty_contexts(self, mock_embed, mock_gen, mock_init):
        """Test context precision with empty contexts."""
        mock_embed.from_pretrained.return_value = MagicMock()
        mock_gen.return_value = MagicMock()
        
        evaluator = RAGASEvaluator(project="test-project", location="us-central1")
        
        score = evaluator._context_precision(question="Test?", contexts=[])
        
        assert score == 0.0


class TestContextRecall:
    """Test _context_recall method."""
    
    @patch('app.rag.ragas_eval.aiplatform.init')
    @patch('app.rag.ragas_eval.GenerativeModel')
    @patch('app.rag.ragas_eval.TextEmbeddingModel')
    def test_context_recall_basic(self, mock_embed, mock_gen, mock_init):
        """Test context recall calculation."""
        mock_embed_instance = MagicMock()
        mock_embed_instance.get_embeddings.return_value = [MagicMock(values=[0.6] * 768)]
        mock_embed.from_pretrained.return_value = mock_embed_instance
        mock_gen.return_value = MagicMock()
        
        evaluator = RAGASEvaluator(project="test-project", location="us-central1")
        
        score = evaluator._context_recall(
            answer="Python is great",
            contexts=["Python is a great language"]
        )
        
        assert 0 <= score <= 1


class TestToxicity:
    """Test _toxicity method."""
    
    @patch('app.rag.ragas_eval.aiplatform.init')
    @patch('app.rag.ragas_eval.GenerativeModel')
    @patch('app.rag.ragas_eval.TextEmbeddingModel')
    def test_toxicity_clean_text(self, mock_embed, mock_gen, mock_init):
        """Test toxicity with clean text."""
        mock_embed.from_pretrained.return_value = MagicMock()
        
        mock_gen_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "0"
        mock_gen_instance.generate_content.return_value = mock_response
        mock_gen.return_value = mock_gen_instance
        
        evaluator = RAGASEvaluator(project="test-project", location="us-central1")
        
        score = evaluator._toxicity("This is a polite and helpful response")
        
        assert 0 <= score <= 1
    
    @patch('app.rag.ragas_eval.aiplatform.init')
    @patch('app.rag.ragas_eval.GenerativeModel')
    @patch('app.rag.ragas_eval.TextEmbeddingModel')
    def test_toxicity_empty_text(self, mock_embed, mock_gen, mock_init):
        """Test toxicity with empty text."""
        mock_embed.from_pretrained.return_value = MagicMock()
        mock_gen.return_value = MagicMock()
        
        evaluator = RAGASEvaluator(project="test-project", location="us-central1")
        
        score = evaluator._toxicity("")
        
        assert score == 0.0


class TestCosineSimilarity:
    """Test _cosine_similarity method."""
    
    @patch('app.rag.ragas_eval.aiplatform.init')
    @patch('app.rag.ragas_eval.GenerativeModel')
    @patch('app.rag.ragas_eval.TextEmbeddingModel')
    def test_cosine_similarity_identical(self, mock_embed, mock_gen, mock_init):
        """Test cosine similarity of identical vectors."""
        mock_embed.from_pretrained.return_value = MagicMock()
        mock_gen.return_value = MagicMock()
        
        evaluator = RAGASEvaluator(project="test-project", location="us-central1")
        
        vec = [1.0, 0.5, 0.3]
        similarity = evaluator._cosine_similarity(vec, vec)
        
        assert abs(similarity - 1.0) < 0.01
    
    @patch('app.rag.ragas_eval.aiplatform.init')
    @patch('app.rag.ragas_eval.GenerativeModel')
    @patch('app.rag.ragas_eval.TextEmbeddingModel')
    def test_cosine_similarity_orthogonal(self, mock_embed, mock_gen, mock_init):
        """Test cosine similarity of orthogonal vectors."""
        mock_embed.from_pretrained.return_value = MagicMock()
        mock_gen.return_value = MagicMock()
        
        evaluator = RAGASEvaluator(project="test-project", location="us-central1")
        
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = evaluator._cosine_similarity(vec1, vec2)
        
        assert abs(similarity - 0.0) < 0.01


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @patch('app.rag.ragas_eval.aiplatform.init')
    @patch('app.rag.ragas_eval.GenerativeModel')
    @patch('app.rag.ragas_eval.TextEmbeddingModel')
    def test_evaluate_empty_answer(self, mock_embed, mock_gen, mock_init):
        """Test evaluation with empty answer."""
        mock_embed.from_pretrained.return_value = MagicMock()
        mock_gen.return_value = MagicMock()
        
        evaluator = RAGASEvaluator(project="test-project", location="us-central1")
        
        # Should handle gracefully
        result = evaluator.evaluate(
            question="Test?",
            answer="",
            contexts=["Context"],
            ground_truth=None
        )
        
        assert isinstance(result, RAGASMetrics)
    
    @patch('app.rag.ragas_eval.aiplatform.init')
    @patch('app.rag.ragas_eval.GenerativeModel')
    @patch('app.rag.ragas_eval.TextEmbeddingModel')
    def test_evaluate_empty_question(self, mock_embed, mock_gen, mock_init):
        """Test evaluation with empty question."""
        mock_embed.from_pretrained.return_value = MagicMock()
        mock_gen.return_value = MagicMock()
        
        evaluator = RAGASEvaluator(project="test-project", location="us-central1")
        
        result = evaluator.evaluate(
            question="",
            answer="Answer",
            contexts=["Context"],
            ground_truth=None
        )
        
        assert isinstance(result, RAGASMetrics)
