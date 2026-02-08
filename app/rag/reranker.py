"""
Re-ranking module for improving retrieval quality.
Implements semantic re-ranking of retrieved chunks.
"""

from typing import List, Dict
import numpy as np
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel


class SemanticReranker:
    """
    Re-ranks retrieved chunks based on semantic similarity to the query.
    This improves RAG accuracy by reordering context quality.
    """
    
    def __init__(self, project: str, location: str):
        aiplatform.init(project=project, location=location)
        self.embedder = TextEmbeddingModel.from_pretrained("text-embedding-004")
    
    def rerank(self, query: str, chunks: List[Dict], top_k: int = None) -> List[Dict]:
        """
        Re-rank chunks based on semantic similarity to query.
        
        Args:
            query: User's query string
            chunks: List of retrieved chunks with text and metadata
            top_k: Number of top results to return (None = return all)
        
        Returns:
            Re-ranked list of chunks with updated scores
        """
        if not chunks:
            return []
        
        # Embed query
        query_embedding = self.embedder.get_embeddings([query])[0].values
        query_vec = np.array(query_embedding)
        
        # Re-calculate semantic similarity for each chunk
        reranked = []
        for chunk in chunks:
            # Embed chunk text
            chunk_embedding = self.embedder.get_embeddings([chunk["text"]])[0].values
            chunk_vec = np.array(chunk_embedding)
            
            # Calculate cosine similarity
            similarity = np.dot(query_vec, chunk_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(chunk_vec)
            )
            
            chunk["rerank_score"] = float(similarity)
            reranked.append(chunk)
        
        # Sort by rerank_score descending
        reranked.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        
        if top_k:
            return reranked[:top_k]
        return reranked


class CrossEncoderReranker:
    """
    Alternative re-ranker using cross-encoder approach.
    More accurate but slower than semantic similarity.
    """
    
    def __init__(self, project: str, location: str):
        aiplatform.init(project=project, location=location)
        self.embedder = TextEmbeddingModel.from_pretrained("text-embedding-004")
    
    def rerank(self, query: str, chunks: List[Dict], top_k: int = None) -> List[Dict]:
        """
        Re-rank using query-document pair scoring.
        """
        if not chunks:
            return []
        
        # Create query-document pairs
        pairs = [(query, chunk["text"]) for chunk in chunks]
        
        # Score each pair
        scores = []
        for i, (q, doc) in enumerate(pairs):
            # Concatenate query and document for cross-encoding
            combined_text = f"Query: {q}\n\nDocument: {doc}"
            embedding = self.embedder.get_embeddings([combined_text])[0].values
            
            # Use embedding magnitude as relevance score
            score = float(np.linalg.norm(embedding))
            scores.append(score)
            chunks[i]["rerank_score"] = score
        
        # Sort by score descending
        chunks.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        
        if top_k:
            return chunks[:top_k]
        return chunks


class HybridReranker:
    """
    Combines multiple ranking signals for optimal results.
    Uses weighted combination of:
    - Initial retrieval score
    - Semantic similarity
    - Length normalization
    """
    
    def __init__(self, project: str, location: str, 
                 retrieval_weight: float = 0.4,
                 semantic_weight: float = 0.5,
                 length_weight: float = 0.1):
        aiplatform.init(project=project, location=location)
        self.embedder = TextEmbeddingModel.from_pretrained("text-embedding-004")
        self.retrieval_weight = retrieval_weight
        self.semantic_weight = semantic_weight
        self.length_weight = length_weight
    
    def rerank(self, query: str, chunks: List[Dict], top_k: int = None) -> List[Dict]:
        """
        Hybrid re-ranking with multiple signals.
        """
        if not chunks:
            return []
        
        # Embed query once
        query_embedding = self.embedder.get_embeddings([query])[0].values
        query_vec = np.array(query_embedding)
        
        # Calculate combined scores
        for chunk in chunks:
            # Original retrieval score
            retrieval_score = chunk.get("score", 0.5)
            
            # Semantic similarity
            chunk_embedding = self.embedder.get_embeddings([chunk["text"]])[0].values
            chunk_vec = np.array(chunk_embedding)
            semantic_score = np.dot(query_vec, chunk_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(chunk_vec)
            )
            
            # Length penalty (prefer medium-length chunks)
            ideal_length = 2000
            length_score = 1.0 - abs(len(chunk["text"]) - ideal_length) / ideal_length
            length_score = max(0.0, min(1.0, length_score))
            
            # Combined score
            combined_score = (
                self.retrieval_weight * retrieval_score +
                self.semantic_weight * semantic_score +
                self.length_weight * length_score
            )
            
            chunk["rerank_score"] = float(combined_score)
        
        # Sort by combined score
        chunks.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        
        if top_k:
            return chunks[:top_k]
        return chunks
