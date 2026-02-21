"""
Template matching engine for compliance checking.
Matches document sections to template requirements using semantic similarity.
"""

from typing import List, Dict, Optional
import numpy as np
from app.logging_config import get_logger

logger = get_logger(__name__)


class TemplateMatcher:
    """Match document sections to template requirements using embeddings."""
    
    def __init__(self, embedder, similarity_threshold: float = 0.75):
        """
        Initialize template matcher.
        
        Args:
            embedder: Text embedder for semantic similarity
            similarity_threshold: Minimum similarity score for match (0.0-1.0)
        """
        self.embedder = embedder
        self.similarity_threshold = similarity_threshold
        logger.info(f"TemplateMatcher initialized with threshold={similarity_threshold}")
    
    def match(
        self,
        document_text: str,
        templates: List[Dict],
        top_k: int = 5
    ) -> List[Dict]:
        """
        Match document sections to template requirements.
        
        Args:
            document_text: Full document text
            templates: List of template chunks with requirements
            top_k: Number of best matches to return per requirement
        
        Returns:
            List of matched sections with similarity scores
        """
        try:
            # Extract requirements from templates
            requirements = self._extract_requirements(templates)
            if not requirements:
                logger.warning("No requirements found in templates")
                return []
            
            # Chunk document into sections
            doc_sections = self._chunk_document(document_text)
            if not doc_sections:
                logger.warning("No sections extracted from document")
                return []
            
            logger.info(f"Matching {len(requirements)} requirements against {len(doc_sections)} document sections")
            
            # Embed requirements and document sections
            req_texts = [r["text"] for r in requirements]
            doc_texts = [s["text"] for s in doc_sections]
            
            req_embeddings = self.embedder.embed(req_texts)
            doc_embeddings = self.embedder.embed(doc_texts)
            
            # Convert to numpy arrays for efficient computation
            req_vectors = np.array(req_embeddings)
            doc_vectors = np.array(doc_embeddings)
            
            # Compute cosine similarity matrix
            similarity_matrix = self._cosine_similarity_matrix(req_vectors, doc_vectors)
            
            # Match each requirement to best document section
            matched_sections = []
            for i, requirement in enumerate(requirements):
                similarities = similarity_matrix[i]
                
                # Get top-k matches
                top_indices = np.argsort(similarities)[-top_k:][::-1]
                
                for rank, idx in enumerate(top_indices):
                    score = float(similarities[idx])
                    
                    match_status = "compliant" if score >= self.similarity_threshold else "partial" if score >= 0.6 else "missing"
                    
                    matched_sections.append({
                        "requirement_id": requirement["id"],
                        "requirement_text": requirement["text"],
                        "requirement_category": requirement.get("category", "general"),
                        "matched_section": doc_sections[idx]["text"] if score >= 0.6 else None,
                        "section_id": doc_sections[idx]["id"] if score >= 0.6 else None,
                        "similarity_score": score,
                        "rank": rank + 1,
                        "status": match_status
                    })
            
            # Filter to keep only best match per requirement
            best_matches = {}
            for match in matched_sections:
                req_id = match["requirement_id"]
                if req_id not in best_matches or match["similarity_score"] > best_matches[req_id]["similarity_score"]:
                    best_matches[req_id] = match
            
            result = list(best_matches.values())
            logger.info(f"Matched {len(result)} requirements: {sum(1 for m in result if m['status'] == 'compliant')} compliant")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in template matching: {e}", exc_info=True)
            return []
    
    def _extract_requirements(self, templates: List[Dict]) -> List[Dict]:
        """
        Extract structured requirements from template chunks.
        
        Args:
            templates: List of template chunks
        
        Returns:
            List of requirement dictionaries
        """
        requirements = []
        
        for template in templates:
            text = template.get("text", "")
            metadata = template.get("metadata", {})
            
            # Split template into requirement sentences
            # Look for common patterns: numbered lists, bullet points, "shall", "must", "should"
            sentences = self._split_into_requirements(text)
            
            for idx, sentence in enumerate(sentences):
                if len(sentence.strip()) > 20:  # Filter out too short sentences
                    requirements.append({
                        "id": f"{metadata.get('template_id', 'template')}_{metadata.get('chunk_id', idx)}",
                        "text": sentence.strip(),
                        "category": metadata.get("template_type", "general"),
                        "template_id": metadata.get("template_id"),
                        "source": template.get("id", "")
                    })
        
        return requirements
    
    def _split_into_requirements(self, text: str) -> List[str]:
        """
        Split template text into individual requirements.
        
        Args:
            text: Template text
        
        Returns:
            List of requirement sentences
        """
        # Simple sentence splitting (can be enhanced with NLP)
        import re
        
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Also split on numbered lists
        requirements = []
        for sentence in sentences:
            # Split on patterns like "1.", "a)", "(i)"
            parts = re.split(r'(?:^|\n)\s*(?:\d+\.|\w\)|\([a-z]+\))\s+', sentence)
            requirements.extend([p.strip() for p in parts if p.strip()])
        
        return requirements
    
    def _chunk_document(self, document_text: str, chunk_size: int = 500) -> List[Dict]:
        """
        Chunk document into logical sections for matching.
        
        Args:
            document_text: Full document text
            chunk_size: Approximate number of words per chunk
        
        Returns:
            List of document sections
        """
        words = document_text.split()
        chunks = []
        
        # Sliding window with 50% overlap
        step_size = chunk_size // 2
        
        for i in range(0, len(words), step_size):
            chunk_words = words[i:i + chunk_size]
            if len(chunk_words) < 50:  # Skip very small chunks at the end
                continue
            
            chunk_text = ' '.join(chunk_words)
            chunks.append({
                "id": f"section_{i}",
                "text": chunk_text,
                "start_word": i,
                "end_word": min(i + chunk_size, len(words))
            })
        
        return chunks
    
    @staticmethod
    def _cosine_similarity_matrix(matrix_a: np.ndarray, matrix_b: np.ndarray) -> np.ndarray:
        """
        Compute cosine similarity between two matrices.
        
        Args:
            matrix_a: First matrix (n x d)
            matrix_b: Second matrix (m x d)
        
        Returns:
            Similarity matrix (n x m)
        """
        # Normalize vectors
        norm_a = np.linalg.norm(matrix_a, axis=1, keepdims=True)
        norm_b = np.linalg.norm(matrix_b, axis=1, keepdims=True)
        
        matrix_a_normalized = matrix_a / (norm_a + 1e-8)
        matrix_b_normalized = matrix_b / (norm_b + 1e-8)
        
        # Compute dot product
        similarity = np.dot(matrix_a_normalized, matrix_b_normalized.T)
        
        return similarity
