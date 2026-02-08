"""
Prompt compression and optimization for long contexts.
Reduces token usage while preserving semantic meaning.
"""

from typing import List, Dict, Any, Tuple
import re
from app.logging_config import get_logger

logger = get_logger(__name__)


class PromptCompressor:
    """
    Compresses prompts to reduce token count.
    
    Techniques:
    - Remove redundant whitespace
    - Eliminate filler words
    - Semantic deduplication
    - Context truncation with importance scoring
    """
    
    # Filler words that can be removed with minimal impact
    FILLER_WORDS = {
        "actually", "basically", "essentially", "literally", "really",
        "very", "quite", "rather", "somewhat", "just", "simply",
        "in fact", "as a matter of fact", "to be honest"
    }
    
    def __init__(self, max_tokens: int = 6000):
        """
        Initialize compressor.
        
        Args:
            max_tokens: Maximum tokens to allow in compressed prompt
        """
        self.max_tokens = max_tokens
        # Rough approximation: 1 token ≈ 4 characters
        self.max_chars = max_tokens * 4
    
    def compress_whitespace(self, text: str) -> str:
        """
        Remove excessive whitespace.
        
        Args:
            text: Input text
        
        Returns:
            Text with normalized whitespace
        """
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple newlines with double newline (preserve paragraphs)
        text = re.sub(r'\n\n+', '\n\n', text)
        
        # Remove trailing/leading whitespace
        text = text.strip()
        
        return text
    
    def remove_fillers(self, text: str) -> str:
        """
        Remove filler words.
        
        Args:
            text: Input text
        
        Returns:
            Text with filler words removed
        """
        words = text.split()
        filtered = [
            word for word in words
            if word.lower() not in self.FILLER_WORDS
        ]
        return ' '.join(filtered)
    
    def score_sentence_importance(
        self,
        sentence: str,
        question: str
    ) -> float:
        """
        Score sentence importance relative to question.
        
        Args:
            sentence: Sentence to score
            question: User's question
        
        Returns:
            Importance score (0-1)
        """
        # Simple keyword overlap scoring
        question_words = set(question.lower().split())
        sentence_words = set(sentence.lower().split())
        
        # Remove common words
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        question_words -= stopwords
        sentence_words -= stopwords
        
        if not question_words:
            return 0.5  # Default score
        
        # Calculate overlap
        overlap = len(question_words & sentence_words)
        score = overlap / len(question_words)
        
        # Bonus for exact phrase matches
        if any(word in sentence.lower() for word in question.lower().split() if len(word) > 4):
            score += 0.2
        
        return min(score, 1.0)
    
    def compress_contexts(
        self,
        contexts: List[str],
        question: str,
        preserve_top_n: int = 3
    ) -> List[str]:
        """
        Compress context chunks while preserving most relevant information.
        
        Args:
            contexts: List of context chunks
            question: User's question
            preserve_top_n: Number of top contexts to preserve fully
        
        Returns:
            Compressed contexts
        """
        if not contexts:
            return []
        
        compressed = []
        current_length = 0
        
        # Always preserve top N contexts (most relevant)
        for i, context in enumerate(contexts[:preserve_top_n]):
            # Apply basic compression
            compressed_ctx = self.compress_whitespace(context)
            compressed_ctx = self.remove_fillers(compressed_ctx)
            
            compressed.append(compressed_ctx)
            current_length += len(compressed_ctx)
            
            if current_length >= self.max_chars:
                logger.info(
                    "Reached max length after preserving top contexts",
                    num_contexts=i + 1
                )
                return compressed
        
        # For remaining contexts, use importance scoring
        remaining_contexts = contexts[preserve_top_n:]
        
        # Score each sentence in remaining contexts
        scored_sentences = []
        for context in remaining_contexts:
            sentences = re.split(r'[.!?]+', context)
            for sentence in sentences:
                if len(sentence.strip()) < 10:  # Skip very short sentences
                    continue
                
                score = self.score_sentence_importance(sentence, question)
                scored_sentences.append((sentence.strip(), score))
        
        # Sort by importance
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        # Add sentences until we hit the limit
        remaining_text = []
        for sentence, score in scored_sentences:
            if current_length + len(sentence) > self.max_chars:
                break
            
            remaining_text.append(sentence)
            current_length += len(sentence)
        
        # Combine remaining sentences into a single context
        if remaining_text:
            compressed.append(". ".join(remaining_text) + ".")
        
        logger.info(
            "Contexts compressed",
            original_count=len(contexts),
            compressed_count=len(compressed),
            original_chars=sum(len(c) for c in contexts),
            compressed_chars=current_length
        )
        
        return compressed
    
    def build_compressed_prompt(
        self,
        question: str,
        contexts: List[str],
        system_instruction: str = ""
    ) -> str:
        """
        Build a compressed prompt with question and contexts.
        
        Args:
            question: User's question
            contexts: Context chunks
            system_instruction: System-level instruction
        
        Returns:
            Compressed prompt
        """
        # Compress contexts
        compressed_contexts = self.compress_contexts(contexts, question)
        
        # Build prompt
        prompt_parts = []
        
        if system_instruction:
            prompt_parts.append(self.compress_whitespace(system_instruction))
        
        # Add contexts
        if compressed_contexts:
            prompt_parts.append("Context:")
            for i, ctx in enumerate(compressed_contexts, 1):
                prompt_parts.append(f"[{i}] {ctx}")
        
        # Add question
        prompt_parts.append(f"\nQuestion: {question}")
        prompt_parts.append("\nAnswer based strictly on the provided context:")
        
        full_prompt = "\n".join(prompt_parts)
        
        # Final whitespace compression
        full_prompt = self.compress_whitespace(full_prompt)
        
        logger.info(
            "Prompt built",
            total_length=len(full_prompt),
            estimated_tokens=len(full_prompt) // 4
        )
        
        return full_prompt


class SemanticFilter:
    """
    Filters retrieved chunks based on semantic relevance.
    Prevents low-quality or irrelevant chunks from reaching the LLM.
    """
    
    def __init__(
        self,
        min_similarity: float = 0.3,
        max_chunks: int = 5
    ):
        """
        Initialize semantic filter.
        
        Args:
            min_similarity: Minimum similarity score threshold
            max_chunks: Maximum chunks to pass through
        """
        self.min_similarity = min_similarity
        self.max_chunks = max_chunks
    
    def filter_chunks(
        self,
        chunks: List[Dict[str, Any]],
        question: str
    ) -> List[Dict[str, Any]]:
        """
        Filter chunks based on relevance and quality.
        
        Args:
            chunks: Retrieved chunks with scores
            question: User's question
        
        Returns:
            Filtered chunks
        """
        if not chunks:
            return []
        
        filtered = []
        
        for chunk in chunks:
            score = chunk.get("score", 0.0)
            text = chunk.get("text", "")
            
            # Skip if below similarity threshold
            if score < self.min_similarity:
                logger.debug(
                    "Chunk filtered (low similarity)",
                    score=score,
                    threshold=self.min_similarity
                )
                continue
            
            # Skip if too short (likely not useful)
            if len(text.strip()) < 20:
                logger.debug("Chunk filtered (too short)")
                continue
            
            # Skip if appears to be junk (high ratio of special characters)
            special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
            if special_chars / max(len(text), 1) > 0.3:
                logger.debug("Chunk filtered (too many special characters)")
                continue
            
            filtered.append(chunk)
            
            # Stop if we have enough
            if len(filtered) >= self.max_chunks:
                break
        
        logger.info(
            "Chunks filtered",
            original=len(chunks),
            filtered=len(filtered),
            removed=len(chunks) - len(filtered)
        )
        
        return filtered
    
    def deduplicate_chunks(
        self,
        chunks: List[Dict[str, Any]],
        similarity_threshold: float = 0.85
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate or highly similar chunks.
        
        Args:
            chunks: List of chunks
            similarity_threshold: Similarity threshold for deduplication
        
        Returns:
            Deduplicated chunks
        """
        if not chunks:
            return []
        
        def jaccard_similarity(text1: str, text2: str) -> float:
            """Calculate Jaccard similarity between two texts."""
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            
            return intersection / union if union > 0 else 0.0
        
        deduplicated = []
        
        for chunk in chunks:
            text = chunk.get("text", "")
            
            # Check similarity with already selected chunks
            is_duplicate = False
            for selected in deduplicated:
                selected_text = selected.get("text", "")
                similarity = jaccard_similarity(text, selected_text)
                
                if similarity >= similarity_threshold:
                    logger.debug(
                        "Chunk skipped (duplicate)",
                        similarity=similarity
                    )
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated.append(chunk)
        
        if len(deduplicated) < len(chunks):
            logger.info(
                "Chunks deduplicated",
                original=len(chunks),
                unique=len(deduplicated),
                removed=len(chunks) - len(deduplicated)
            )
        
        return deduplicated
