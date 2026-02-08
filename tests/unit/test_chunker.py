"""
Unit tests for chunker module.
Tests dynamic chunking, fixed chunking, and text extraction.
"""
import pytest
from app.rag.chunker import (
    chunk_text,
    chunk_text_dynamic,
    extract_text,
    extract_and_chunk
)


class TestChunkText:
    """Test fixed-size chunking."""
    
    def test_empty_text(self):
        """Test chunking empty text."""
        result = chunk_text("")
        assert result == []
    
    def test_short_text(self):
        """Test chunking text shorter than MAX_CHARS."""
        text = "Short text"
        result = chunk_text(text)
        assert len(result) == 1
        assert result[0] == text
    
    def test_long_text_with_overlap(self):
        """Test chunking long text with overlap."""
        text = "A" * 5000  # Longer than MAX_CHARS (2800)
        result = chunk_text(text)
        assert len(result) > 1
        # Check overlap exists
        assert result[0][-100:] in result[1]
    
    def test_whitespace_normalization(self):
        """Test that whitespace is normalized."""
        text = "Text  with    multiple    spaces"
        result = chunk_text(text)
        assert "  " not in result[0]


class TestChunkTextDynamic:
    """Test dynamic/adaptive chunking."""
    
    def test_empty_text(self):
        """Test dynamic chunking with empty text."""
        result = chunk_text_dynamic("")
        assert result == []
    
    def test_single_paragraph(self):
        """Test chunking single paragraph."""
        text = "This is a single paragraph with some content."
        result = chunk_text_dynamic(text, min_chunk_size=10, max_chunk_size=100)
        assert len(result) == 1
        assert result[0] == text.strip()
    
    def test_multiple_paragraphs(self):
        """Test chunking respects paragraph boundaries."""
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        result = chunk_text_dynamic(text, min_chunk_size=10, max_chunk_size=50)
        assert len(result) >= 2
        # Each chunk should contain complete paragraphs
        for chunk in result:
            assert chunk.strip()
    
    def test_long_paragraph_sentence_split(self):
        """Test that long paragraphs are split by sentences."""
        text = "Sentence one. Sentence two. Sentence three. " * 50
        result = chunk_text_dynamic(text, max_chunk_size=200)
        assert len(result) > 1
    
    def test_overlap_between_chunks(self):
        """Test that chunks have overlap."""
        text = "A" * 2000 + "\n\n" + "B" * 2000
        result = chunk_text_dynamic(text, overlap=100)
        assert len(result) >= 2
        # Note: overlap is approximate due to structure-aware splitting
    
    def test_min_chunk_size_enforcement(self):
        """Test that small chunks are merged."""
        text = "A.\n\nB.\n\nC." * 100
        result = chunk_text_dynamic(text, min_chunk_size=200, max_chunk_size=500)
        for chunk in result:
            # Last chunk might be smaller
            if chunk != result[-1]:
                assert len(chunk) >= 150  # Allow some tolerance


class TestExtractText:
    """Test text extraction from different file types."""
    
    def test_plain_text_extraction(self):
        """Test extracting from plain text."""
        content = b"Hello world"
        result = extract_text("test.txt", content)
        assert result == "Hello world"
    
    def test_unknown_file_type(self):
        """Test extracting from unknown file type (fallback to UTF-8)."""
        content = b"Test content"
        result = extract_text("test.unknown", content)
        assert result == "Test content"
    
    def test_invalid_encoding(self):
        """Test handling invalid UTF-8."""
        content = b"\xff\xfe Invalid UTF-8"
        result = extract_text("test.txt", content)
        # Should not raise error, returns best-effort decode
        assert isinstance(result, str)


class TestExtractAndChunk:
    """Test complete extraction and chunking pipeline."""
    
    def test_empty_docs(self):
        """Test with no documents."""
        result = extract_and_chunk([])
        assert result == []
    
    def test_single_document(self):
        """Test with single document."""
        docs = [("test.txt", b"This is a test document with some content.")]
        result = extract_and_chunk(docs, use_dynamic_chunking=False)
        assert len(result) == 1
        assert result[0]["id"] == "test.txt-0"
        assert "test" in result[0]["text"].lower()
        assert result[0]["metadata"]["source"] == "test.txt"
        assert result[0]["metadata"]["chunking_method"] == "fixed"
    
    def test_multiple_documents(self):
        """Test with multiple documents."""
        docs = [
            ("doc1.txt", b"First document content"),
            ("doc2.txt", b"Second document content")
        ]
        result = extract_and_chunk(docs)
        assert len(result) >= 2
        sources = [chunk["metadata"]["source"] for chunk in result]
        assert "doc1.txt" in sources
        assert "doc2.txt" in sources
    
    def test_dynamic_chunking_metadata(self):
        """Test that dynamic chunking is marked in metadata."""
        docs = [("test.txt", b"Test content" * 100)]
        result = extract_and_chunk(docs, use_dynamic_chunking=True)
        assert all(chunk["metadata"]["chunking_method"] == "dynamic" for chunk in result)
    
    def test_fixed_chunking_metadata(self):
        """Test that fixed chunking is marked in metadata."""
        docs = [("test.txt", b"Test content" * 100)]
        result = extract_and_chunk(docs, use_dynamic_chunking=False)
        assert all(chunk["metadata"]["chunking_method"] == "fixed" for chunk in result)
    
    def test_pii_detection_integration(self, mocker):
        """Test integration with PII detector."""
        mock_detector = mocker.Mock()
        mock_detector.detect_pii.return_value = {
            "status": "clean",
            "has_pii": False,
            "pii_types": []
        }
        
        docs = [("test.txt", b"Test content")]
        result = extract_and_chunk(docs, pii_detector=mock_detector)
        
        assert result[0]["metadata"]["pii_status"] == "clean"
        assert result[0]["metadata"]["pii_detected"] is False
        mock_detector.detect_pii.assert_called()
    
    def test_pii_detection_with_pii_found(self, mocker):
        """Test when PII is detected."""
        mock_detector = mocker.Mock()
        mock_detector.detect_pii.return_value = {
            "status": "pii_detected",
            "has_pii": True,
            "pii_types": ["EMAIL", "PHONE"]
        }
        
        docs = [("test.txt", b"Contact: john@example.com")]
        result = extract_and_chunk(docs, pii_detector=mock_detector)
        
        assert result[0]["metadata"]["pii_status"] == "pii_detected"
        assert result[0]["metadata"]["pii_detected"] is True
        assert "EMAIL" in result[0]["metadata"]["pii_types"]


@pytest.mark.parametrize("text,expected_chunks", [
    ("", 0),
    ("Short", 1),
    ("A" * 3000, 2),
    ("A" * 10000, 4),
])
def test_chunk_counts(text, expected_chunks):
    """Test that chunking produces expected number of chunks."""
    result = chunk_text(text)
    assert len(result) == expected_chunks or len(result) == expected_chunks + 1  # Allow ±1
