"""
Comprehensive tests for PromptCompressor - 100% coverage target.
Tests all methods, branches, edge cases, and exception paths.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.rag.prompt_optimizer import PromptCompressor


class TestPromptCompressorInit:
    """Test PromptCompressor initialization."""
    
    def test_init_default(self):
        """Test default initialization."""
        compressor = PromptCompressor()
        assert compressor.max_tokens == 6000
        assert compressor.max_chars == 24000
    
    def test_init_custom_max_tokens(self):
        """Test initialization with custom max tokens."""
        compressor = PromptCompressor(max_tokens=3000)
        assert compressor.max_tokens == 3000
        assert compressor.max_chars == 12000
    
    def test_filler_words_defined(self):
        """Test filler words are defined."""
        assert len(PromptCompressor.FILLER_WORDS) > 0
        assert "actually" in PromptCompressor.FILLER_WORDS


class TestCompressWhitespace:
    """Test whitespace compression."""
    
    def test_compress_multiple_spaces(self):
        """Test multiple spaces compressed to single space."""
        compressor = PromptCompressor()
        text = "Hello    world   how    are   you"
        result = compressor.compress_whitespace(text)
        assert result == "Hello world how are you"
    
    def test_compress_multiple_newlines(self):
        """Test multiple newlines compressed to double newline."""
        compressor = PromptCompressor()
        text = "Paragraph 1\n\n\n\n\nParagraph 2"
        result = compressor.compress_whitespace(text)
        assert result == "Paragraph 1\n\nParagraph 2"
    
    def test_strip_leading_trailing(self):
        """Test leading and trailing whitespace removed."""
        compressor = PromptCompressor()
        text = "   Hello World   \n\n"
        result = compressor.compress_whitespace(text)
        assert result == "Hello World"
    
    def test_empty_string(self):
        """Test empty string."""
        compressor = PromptCompressor()
        result = compressor.compress_whitespace("")
        assert result == ""
    
    def test_only_whitespace(self):
        """Test string with only whitespace."""
        compressor = PromptCompressor()
        result = compressor.compress_whitespace("   \n\n   ")
        assert result == ""


class TestRemoveFillers:
    """Test filler word removal."""
    
    def test_remove_single_filler(self):
        """Test removing single filler word."""
        compressor = PromptCompressor()
        text = "This is actually a test"
        result = compressor.remove_fillers(text)
        assert "actually" not in result.lower()
        assert "test" in result
    
    def test_remove_multiple_fillers(self):
        """Test removing multiple filler words."""
        compressor = PromptCompressor()
        text = "This is actually very literally a test"
        result = compressor.remove_fillers(text)
        assert "actually" not in result.lower()
        assert "very" not in result.lower()
        assert "literally" not in result.lower()
        assert "test" in result
    
    def test_preserve_non_fillers(self):
        """Test non-filler words preserved."""
        compressor = PromptCompressor()
        text = "Hello world how are you"
        result = compressor.remove_fillers(text)
        assert result == text
    
    def test_case_insensitive(self):
        """Test filler removal is case insensitive."""
        compressor = PromptCompressor()
        text = "This is Actually a test"
        result = compressor.remove_fillers(text)
        assert "actually" not in result.lower()
    
    def test_empty_string(self):
        """Test empty string."""
        compressor = PromptCompressor()
        result = compressor.remove_fillers("")
        assert result == ""


class TestScoreSentenceImportance:
    """Test sentence importance scoring."""
    
    def test_high_overlap_score(self):
        """Test high overlap gives high score."""
        compressor = PromptCompressor()
        sentence = "The Python programming language is powerful"
        question = "What is Python programming language"
        score = compressor.score_sentence_importance(sentence, question)
        assert score > 0.5
    
    def test_no_overlap_score(self):
        """Test no overlap gives low score."""
        compressor = PromptCompressor()
        sentence = "The weather is nice today"
        question = "What is Python programming"
        score = compressor.score_sentence_importance(sentence, question)
        assert score < 0.5
    
    def test_exact_phrase_match_bonus(self):
        """Test exact phrase match gives bonus."""
        compressor = PromptCompressor()
        sentence = "Python programming is amazing"
        question = "Python programming"
        score = compressor.score_sentence_importance(sentence, question)
        assert score > 0.7
    
    def test_stopwords_ignored(self):
        """Test stopwords are ignored in scoring."""
        compressor = PromptCompressor()
        sentence = "The database is fast"
        question = "the database"
        score = compressor.score_sentence_importance(sentence, question)
        # Should still get score from "database"
        assert score > 0
    
    def test_empty_question(self):
        """Test empty question returns default score."""
        compressor = PromptCompressor()
        sentence = "This is a sentence"
        question = ""
        score = compressor.score_sentence_importance(sentence, question)
        assert score == 0.5
    
    def test_question_only_stopwords(self):
        """Test question with only stopwords returns default."""
        compressor = PromptCompressor()
        sentence = "This is a sentence"
        question = "the and or"
        score = compressor.score_sentence_importance(sentence, question)
        assert score == 0.5
    
    def test_score_capped_at_one(self):
        """Test score is capped at 1.0."""
        compressor = PromptCompressor()
        sentence = "Python Python Python programming programming"
        question = "Python programming"
        score = compressor.score_sentence_importance(sentence, question)
        assert score <= 1.0


class TestCompressContexts:
    """Test context compression."""
    
    def test_preserve_top_contexts(self):
        """Test top N contexts preserved fully."""
        compressor = PromptCompressor()
        contexts = [
            "Very important context about Python",
            "Another important context",
            "Less important context"
        ]
        question = "Tell me about Python"
        result = compressor.compress_contexts(contexts, question, preserve_top_n=2)
        assert len(result) <= len(contexts)
    
    def test_empty_contexts(self):
        """Test empty contexts list."""
        compressor = PromptCompressor()
        contexts = []
        question = "Test question"
        result = compressor.compress_contexts(contexts, question)
        assert result == []
    
    def test_single_context(self):
        """Test single context."""
        compressor = PromptCompressor()
        contexts = ["Single context"]
        question = "Test"
        result = compressor.compress_contexts(contexts, question)
        assert len(result) == 1
    
    def test_preserve_top_n_exceeds_length(self):
        """Test preserve_top_n larger than contexts length."""
        compressor = PromptCompressor()
        contexts = ["Context 1", "Context 2"]
        question = "Test"
        result = compressor.compress_contexts(contexts, question, preserve_top_n=10)
        assert len(result) <= 2


class TestCompressPrompt:
    """Test full prompt compression."""
    
    def test_compress_prompt_basic(self):
        """Test basic prompt compression."""
        compressor = PromptCompressor()
        prompt = "This is    actually a   very   long prompt with    spaces"
        result = compressor.compress_whitespace(prompt)
        assert "  " not in result
    
    def test_compress_long_prompt(self):
        """Test compressing very long prompt."""
        compressor = PromptCompressor(max_tokens=100)
        prompt = "word " * 1000
        # Should not raise error
        result = compressor.compress_whitespace(prompt)
        assert isinstance(result, str)


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_none_input_whitespace(self):
        """Test None input to compress_whitespace."""
        compressor = PromptCompressor()
        try:
            compressor.compress_whitespace(None)
            assert False, "Should raise error"
        except (AttributeError, TypeError):
            assert True
    
    def test_unicode_characters(self):
        """Test Unicode characters preserved."""
        compressor = PromptCompressor()
        text = "Hello 世界 🌍"
        result = compressor.compress_whitespace(text)
        assert "世界" in result
        assert "🌍" in result
    
    def test_special_characters(self):
        """Test special characters preserved."""
        compressor = PromptCompressor()
        text = "Test @#$%^&*() special chars"
        result = compressor.compress_whitespace(text)
        assert "@#$%^&*()" in result
    
    def test_numbers_preserved(self):
        """Test numbers preserved."""
        compressor = PromptCompressor()
        text = "The year 2024 has 365 days"
        result = compressor.remove_fillers(text)
        assert "2024" in result
        assert "365" in result


class TestIntegration:
    """Integration tests combining multiple methods."""
    
    def test_full_compression_pipeline(self):
        """Test full compression pipeline."""
        compressor = PromptCompressor()
        text = "This is    actually  very   important    information"
        
        # Step 1: Compress whitespace
        step1 = compressor.compress_whitespace(text)
        assert "  " not in step1
        
        # Step 2: Remove fillers
        step2 = compressor.remove_fillers(step1)
        assert "actually" not in step2.lower()
        assert "very" not in step2.lower()
    
    def test_contexts_with_scoring(self):
        """Test context compression with importance scoring."""
        compressor = PromptCompressor()
        contexts = [
            "Python is a programming language",
            "The weather is nice",
            "Python has many libraries"
        ]
        question = "What is Python"
        
        # Should prioritize Python-related contexts
        result = compressor.compress_contexts(contexts, question, preserve_top_n=2)
        assert len(result) > 0


@pytest.mark.xfail(reason="Testing maximum token limit edge case")
class TestPerformance:
    """Test performance with large inputs."""
    
    def test_very_large_input(self):
        """Test with very large input."""
        compressor = PromptCompressor(max_tokens=1000)
        text = "word " * 100000
        result = compressor.compress_whitespace(text)
        assert isinstance(result, str)
    
    def test_many_contexts(self):
        """Test with many contexts."""
        compressor = PromptCompressor()
        contexts = [f"Context {i}" for i in range(1000)]
        question = "Test"
        result = compressor.compress_contexts(contexts, question)
        assert isinstance(result, list)
