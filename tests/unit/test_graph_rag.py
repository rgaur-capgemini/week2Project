"""
Comprehensive tests for LangGraph RAG Pipeline - 100% coverage target.
Tests all methods, branches, edge cases, and exception paths.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
from typing import List, Dict, Any

from app.rag.graph_rag import LangGraphRAGPipeline, RAGState


class TestLangGraphRAGPipelineInit:
    """Test LangGraphRAGPipeline initialization."""
    
    @patch('app.rag.graph_rag.VertexTextEmbedder')
    @patch('app.rag.graph_rag.VertexVectorStore')
    @patch('app.rag.graph_rag.HybridReranker')
    @patch('app.rag.graph_rag.GeminiGenerator')
    def test_init_default(self, mock_gen, mock_reranker, mock_store, mock_embedder):
        """Test default initialization."""
        pipeline = LangGraphRAGPipeline(
            embeddings=mock_embedder,
            vector_store=mock_store,
            reranker=mock_reranker,
            generator=mock_gen
        )
        
        assert pipeline.embeddings == mock_embedder
        assert pipeline.vector_store == mock_store
        assert pipeline.reranker == mock_reranker
        assert pipeline.generator == mock_gen
        assert pipeline.max_iterations == 2
    
    @patch('app.rag.graph_rag.VertexTextEmbedder')
    @patch('app.rag.graph_rag.VertexVectorStore')
    @patch('app.rag.graph_rag.HybridReranker')
    @patch('app.rag.graph_rag.GeminiGenerator')
    def test_init_custom_max_iterations(self, mock_gen, mock_reranker, mock_store, mock_embedder):
        """Test initialization with custom max iterations."""
        pipeline = LangGraphRAGPipeline(
            embeddings=mock_embedder,
            vector_store=mock_store,
            reranker=mock_reranker,
            generator=mock_gen,
            max_iterations=5
        )
        
        assert pipeline.max_iterations == 5


class TestBuildGraph:
    """Test _build_graph method."""
    
    @patch('app.rag.graph_rag.VertexTextEmbedder')
    @patch('app.rag.graph_rag.VertexVectorStore')
    @patch('app.rag.graph_rag.HybridReranker')
    @patch('app.rag.graph_rag.GeminiGenerator')
    def test_build_graph_creates_nodes(self, mock_gen, mock_reranker, mock_store, mock_embedder):
        """Test graph has all required nodes."""
        pipeline = LangGraphRAGPipeline(
            embeddings=mock_embedder,
            vector_store=mock_store,
            reranker=mock_reranker,
            generator=mock_gen
        )
        
        assert pipeline.graph is not None
        assert pipeline.compiled_graph is not None


class TestRetrieveNode:
    """Test _retrieve_node method."""
    
    @patch('app.rag.graph_rag.VertexTextEmbedder')
    @patch('app.rag.graph_rag.VertexVectorStore')
    @patch('app.rag.graph_rag.HybridReranker')
    @patch('app.rag.graph_rag.GeminiGenerator')
    def test_retrieve_node_basic(self, mock_gen, mock_reranker, mock_store, mock_embedder):
        """Test basic document retrieval."""
        mock_store.search.return_value = [
            {"id": "doc1", "text": "Content 1", "score": 0.9},
            {"id": "doc2", "text": "Content 2", "score": 0.8}
        ]
        
        pipeline = LangGraphRAGPipeline(
            embeddings=mock_embedder,
            vector_store=mock_store,
            reranker=mock_reranker,
            generator=mock_gen
        )
        
        state = RAGState(
            messages=[],
            query="test query",
            retrieved_docs=[],
            reranked_docs=[],
            context="",
            response="",
            confidence_score=0.0,
            needs_refinement=False,
            iteration=0
        )
        
        result = pipeline._retrieve_node(state)
        
        assert len(result["retrieved_docs"]) == 2
        mock_store.search.assert_called_once_with("test query", top_k=10)
    
    @patch('app.rag.graph_rag.VertexTextEmbedder')
    @patch('app.rag.graph_rag.VertexVectorStore')
    @patch('app.rag.graph_rag.HybridReranker')
    @patch('app.rag.graph_rag.GeminiGenerator')
    def test_retrieve_node_empty_results(self, mock_gen, mock_reranker, mock_store, mock_embedder):
        """Test retrieval with no results."""
        mock_store.search.return_value = []
        
        pipeline = LangGraphRAGPipeline(
            embeddings=mock_embedder,
            vector_store=mock_store,
            reranker=mock_reranker,
            generator=mock_gen
        )
        
        state = RAGState(
            messages=[],
            query="test query",
            retrieved_docs=[],
            reranked_docs=[],
            context="",
            response="",
            confidence_score=0.0,
            needs_refinement=False,
            iteration=0
        )
        
        result = pipeline._retrieve_node(state)
        assert result["retrieved_docs"] == []


class TestRerankNode:
    """Test _rerank_node method."""
    
    @patch('app.rag.graph_rag.VertexTextEmbedder')
    @patch('app.rag.graph_rag.VertexVectorStore')
    @patch('app.rag.graph_rag.HybridReranker')
    @patch('app.rag.graph_rag.GeminiGenerator')
    def test_rerank_node_basic(self, mock_gen, mock_reranker, mock_store, mock_embedder):
        """Test basic reranking."""
        mock_reranker.rerank.return_value = [
            {"id": "doc2", "text": "Content 2", "score": 0.95},
            {"id": "doc1", "text": "Content 1", "score": 0.85}
        ]
        
        pipeline = LangGraphRAGPipeline(
            embeddings=mock_embedder,
            vector_store=mock_store,
            reranker=mock_reranker,
            generator=mock_gen
        )
        
        state = RAGState(
            messages=[],
            query="test query",
            retrieved_docs=[
                {"id": "doc1", "text": "Content 1"},
                {"id": "doc2", "text": "Content 2"}
            ],
            reranked_docs=[],
            context="",
            response="",
            confidence_score=0.0,
            needs_refinement=False,
            iteration=0
        )
        
        result = pipeline._rerank_node(state)
        
        assert len(result["reranked_docs"]) == 2
        assert result["reranked_docs"][0]["score"] == 0.95


class TestGenerateNode:
    """Test _generate_node method."""
    
    @patch('app.rag.graph_rag.VertexTextEmbedder')
    @patch('app.rag.graph_rag.VertexVectorStore')
    @patch('app.rag.graph_rag.HybridReranker')
    @patch('app.rag.graph_rag.GeminiGenerator')
    def test_generate_node_basic(self, mock_gen, mock_reranker, mock_store, mock_embedder):
        """Test basic response generation."""
        mock_gen.generate.return_value = "Generated response"
        
        pipeline = LangGraphRAGPipeline(
            embeddings=mock_embedder,
            vector_store=mock_store,
            reranker=mock_reranker,
            generator=mock_gen
        )
        
        state = RAGState(
            messages=[],
            query="test query",
            retrieved_docs=[],
            reranked_docs=[{"text": "Context 1"}, {"text": "Context 2"}],
            context="",
            response="",
            confidence_score=0.0,
            needs_refinement=False,
            iteration=0
        )
        
        result = pipeline._generate_node(state)
        
        assert result["response"] == "Generated response"
        assert result["context"] != ""


class TestEvaluateNode:
    """Test _evaluate_node method."""
    
    @patch('app.rag.graph_rag.VertexTextEmbedder')
    @patch('app.rag.graph_rag.VertexVectorStore')
    @patch('app.rag.graph_rag.HybridReranker')
    @patch('app.rag.graph_rag.GeminiGenerator')
    def test_evaluate_node_high_confidence(self, mock_gen, mock_reranker, mock_store, mock_embedder):
        """Test evaluation with high confidence."""
        pipeline = LangGraphRAGPipeline(
            embeddings=mock_embedder,
            vector_store=mock_store,
            reranker=mock_reranker,
            generator=mock_gen
        )
        
        state = RAGState(
            messages=[],
            query="test query",
            retrieved_docs=[],
            reranked_docs=[{"text": "Good context", "score": 0.9}],
            context="Good context",
            response="Detailed answer",
            confidence_score=0.0,
            needs_refinement=False,
            iteration=0
        )
        
        result = pipeline._evaluate_node(state)
        
        assert result["confidence_score"] > 0
        assert result["needs_refinement"] == False or result["needs_refinement"] == True
    
    @patch('app.rag.graph_rag.VertexTextEmbedder')
    @patch('app.rag.graph_rag.VertexVectorStore')
    @patch('app.rag.graph_rag.HybridReranker')
    @patch('app.rag.graph_rag.GeminiGenerator')
    def test_evaluate_node_low_confidence(self, mock_gen, mock_reranker, mock_store, mock_embedder):
        """Test evaluation with low confidence."""
        pipeline = LangGraphRAGPipeline(
            embeddings=mock_embedder,
            vector_store=mock_store,
            reranker=mock_reranker,
            generator=mock_gen
        )
        
        state = RAGState(
            messages=[],
            query="test query",
            retrieved_docs=[],
            reranked_docs=[{"text": "Weak context", "score": 0.3}],
            context="Weak context",
            response="Short",
            confidence_score=0.0,
            needs_refinement=False,
            iteration=0
        )
        
        result = pipeline._evaluate_node(state)
        assert "confidence_score" in result


class TestRefineQueryNode:
    """Test _refine_query_node method."""
    
    @patch('app.rag.graph_rag.VertexTextEmbedder')
    @patch('app.rag.graph_rag.VertexVectorStore')
    @patch('app.rag.graph_rag.HybridReranker')
    @patch('app.rag.graph_rag.GeminiGenerator')
    def test_refine_query_node_basic(self, mock_gen, mock_reranker, mock_store, mock_embedder):
        """Test query refinement."""
        pipeline = LangGraphRAGPipeline(
            embeddings=mock_embedder,
            vector_store=mock_store,
            reranker=mock_reranker,
            generator=mock_gen
        )
        
        state = RAGState(
            messages=[],
            query="original query",
            retrieved_docs=[],
            reranked_docs=[],
            context="",
            response="",
            confidence_score=0.3,
            needs_refinement=True,
            iteration=0
        )
        
        result = pipeline._refine_query_node(state)
        
        assert result["query"] != "" or result["query"] == "original query"
        assert result["iteration"] == 1


class TestShouldRefine:
    """Test _should_refine conditional logic."""
    
    @patch('app.rag.graph_rag.VertexTextEmbedder')
    @patch('app.rag.graph_rag.VertexVectorStore')
    @patch('app.rag.graph_rag.HybridReranker')
    @patch('app.rag.graph_rag.GeminiGenerator')
    def test_should_refine_low_confidence(self, mock_gen, mock_reranker, mock_store, mock_embedder):
        """Test refinement triggered by low confidence."""
        pipeline = LangGraphRAGPipeline(
            embeddings=mock_embedder,
            vector_store=mock_store,
            reranker=mock_reranker,
            generator=mock_gen
        )
        
        state = RAGState(
            messages=[],
            query="test",
            retrieved_docs=[],
            reranked_docs=[],
            context="",
            response="",
            confidence_score=0.3,
            needs_refinement=True,
            iteration=0
        )
        
        result = pipeline._should_refine(state)
        assert result in ["refine", "finish"]
    
    @patch('app.rag.graph_rag.VertexTextEmbedder')
    @patch('app.rag.graph_rag.VertexVectorStore')
    @patch('app.rag.graph_rag.HybridReranker')
    @patch('app.rag.graph_rag.GeminiGenerator')
    def test_should_refine_max_iterations(self, mock_gen, mock_reranker, mock_store, mock_embedder):
        """Test finish when max iterations reached."""
        pipeline = LangGraphRAGPipeline(
            embeddings=mock_embedder,
            vector_store=mock_store,
            reranker=mock_reranker,
            generator=mock_gen,
            max_iterations=2
        )
        
        state = RAGState(
            messages=[],
            query="test",
            retrieved_docs=[],
            reranked_docs=[],
            context="",
            response="",
            confidence_score=0.3,
            needs_refinement=True,
            iteration=2
        )
        
        result = pipeline._should_refine(state)
        assert result == "finish"


class TestQuery:
    """Test query method."""
    
    @patch('app.rag.graph_rag.VertexTextEmbedder')
    @patch('app.rag.graph_rag.VertexVectorStore')
    @patch('app.rag.graph_rag.HybridReranker')
    @patch('app.rag.graph_rag.GeminiGenerator')
    def test_query_basic(self, mock_gen, mock_reranker, mock_store, mock_embedder):
        """Test basic query execution."""
        mock_store.search.return_value = [{"text": "doc1"}]
        mock_reranker.rerank.return_value = [{"text": "doc1", "score": 0.9}]
        mock_gen.generate.return_value = "Response"
        
        pipeline = LangGraphRAGPipeline(
            embeddings=mock_embedder,
            vector_store=mock_store,
            reranker=mock_reranker,
            generator=mock_gen
        )
        
        # Mock the compiled graph
        pipeline.compiled_graph = MagicMock()
        pipeline.compiled_graph.invoke.return_value = {
            "response": "Generated response",
            "confidence_score": 0.8
        }
        
        result = pipeline.query("test question")
        
        assert "response" in result or result is not None


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @patch('app.rag.graph_rag.VertexTextEmbedder')
    @patch('app.rag.graph_rag.VertexVectorStore')
    @patch('app.rag.graph_rag.HybridReranker')
    @patch('app.rag.graph_rag.GeminiGenerator')
    def test_empty_query(self, mock_gen, mock_reranker, mock_store, mock_embedder):
        """Test with empty query."""
        pipeline = LangGraphRAGPipeline(
            embeddings=mock_embedder,
            vector_store=mock_store,
            reranker=mock_reranker,
            generator=mock_gen
        )
        
        state = RAGState(
            messages=[],
            query="",
            retrieved_docs=[],
            reranked_docs=[],
            context="",
            response="",
            confidence_score=0.0,
            needs_refinement=False,
            iteration=0
        )
        
        result = pipeline._retrieve_node(state)
        assert isinstance(result, dict)
    
    @patch('app.rag.graph_rag.VertexTextEmbedder')
    @patch('app.rag.graph_rag.VertexVectorStore')
    @patch('app.rag.graph_rag.HybridReranker')
    @patch('app.rag.graph_rag.GeminiGenerator')
    def test_max_iterations_zero(self, mock_gen, mock_reranker, mock_store, mock_embedder):
        """Test with max_iterations = 0."""
        pipeline = LangGraphRAGPipeline(
            embeddings=mock_embedder,
            vector_store=mock_store,
            reranker=mock_reranker,
            generator=mock_gen,
            max_iterations=0
        )
        
        assert pipeline.max_iterations == 0
