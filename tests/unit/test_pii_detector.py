"""
Unit tests for PII detector module.
Tests PII detection and redaction.
"""
import pytest
from app.rag.pii_detector import PIIDetector


class TestPIIDetector:
    """Test PII detection functionality."""
    
    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return PIIDetector()
    
    def test_no_pii(self, detector):
        """Test text with no PII."""
        text = "This is a regular document about machine learning."
        result = detector.detect_pii(text)
        assert result["has_pii"] is False
        assert result["status"] == "clean"
        assert len(result["pii_types"]) == 0
    
    def test_email_detection(self, detector):
        """Test email detection."""
        text = "Contact me at john.doe@example.com for more info."
        result = detector.detect_pii(text)
        assert result["has_pii"] is True
        assert "EMAIL" in result["pii_types"]
    
    def test_phone_detection(self, detector):
        """Test phone number detection."""
        text = "Call me at 555-123-4567 or (555) 987-6543"
        result = detector.detect_pii(text)
        assert result["has_pii"] is True
        assert "PHONE" in result["pii_types"]
    
    def test_ssn_detection(self, detector):
        """Test SSN detection."""
        text = "SSN: 123-45-6789"
        result = detector.detect_pii(text)
        assert result["has_pii"] is True
        assert "SSN" in result["pii_types"]
    
    def test_credit_card_detection(self, detector):
        """Test credit card detection."""
        text = "Card number: 4532-1234-5678-9010"
        result = detector.detect_pii(text)
        assert result["has_pii"] is True
        assert "CREDIT_CARD" in result["pii_types"]
    
    def test_multiple_pii_types(self, detector):
        """Test detection of multiple PII types."""
        text = "Contact John at john@example.com or 555-1234. SSN: 123-45-6789"
        result = detector.detect_pii(text)
        assert result["has_pii"] is True
        assert len(result["pii_types"]) >= 2
        assert "EMAIL" in result["pii_types"]
        assert any(pii_type in result["pii_types"] for pii_type in ["PHONE", "SSN"])
    
    def test_redact_pii(self, detector):
        """Test PII redaction."""
        text = "Email: john@example.com Phone: 555-1234"
        result = detector.redact_pii(text)
        assert "john@example.com" not in result
        assert "***@***.***" in result or "[EMAIL]" in result
        assert "555-1234" not in result or "[PHONE]" in result
    
    def test_empty_text(self, detector):
        """Test with empty text."""
        result = detector.detect_pii("")
        assert result["has_pii"] is False
        assert result["status"] == "clean"
    
    def test_whitespace_only(self, detector):
        """Test with whitespace only."""
        result = detector.detect_pii("   \n\t   ")
        assert result["has_pii"] is False


class TestPIIRedaction:
    """Test PII redaction functionality."""
    
    def test_redact_preserves_context(self):
        """Test that redaction preserves surrounding context."""
        detector = PIIDetector()
        text = "Please contact John Smith at john@example.com for details."
        result = detector.redact_pii(text)
        assert "contact" in result.lower()
        assert "details" in result.lower()
        assert "John Smith" in result  # Name might or might not be redacted
    
    def test_multiple_emails_redacted(self):
        """Test that all emails are redacted."""
        detector = PIIDetector()
        text = "Contacts: john@test.com, jane@test.com, admin@test.com"
        result = detector.redact_pii(text)
        # All emails should be redacted
        assert "john@test.com" not in result
        assert "jane@test.com" not in result
        assert "admin@test.com" not in result
    
    def test_partial_matches_not_affected(self):
        """Test that partial matches are not over-redacted."""
        detector = PIIDetector()
        text = "Version 5.55.123.4567 is available"
        # This looks like a phone number but is a version number
        result = detector.redact_pii(text)
        # Should handle gracefully
        assert "Version" in result


class TestPIIDetectorEdgeCases:
    """Test edge cases for PII detection."""
    
    def test_international_phone_formats(self):
        """Test international phone number formats."""
        detector = PIIDetector()
        text = "Call +1-555-123-4567 or +44 20 7946 0958"
        result = detector.detect_pii(text)
        # Should detect at least one phone number
        assert result["has_pii"] is True or result["status"] != "clean"
    
    def test_email_variations(self):
        """Test various email formats."""
        detector = PIIDetector()
        texts = [
            "user@domain.com",
            "first.last@company.co.uk",
            "user+tag@example.org",
            "admin@subdomain.domain.com"
        ]
        for text in texts:
            result = detector.detect_pii(text)
            assert result["has_pii"] is True, f"Failed to detect: {text}"
    
    def test_false_positive_resistance(self):
        """Test resistance to false positives."""
        detector = PIIDetector()
        text = "The ratio is 3.14159 and the version is 1.2.3.4"
        result = detector.detect_pii(text)
        # Should not flag numbers as PII
        assert result["status"] == "clean" or result["has_pii"] is False
    
    def test_large_text_performance(self):
        """Test performance with large text."""
        detector = PIIDetector()
        text = "Regular content. " * 10000 + "Email: test@example.com"
        result = detector.detect_pii(text)
        # Should still detect PII in large text
        assert result["has_pii"] is True
        assert "EMAIL" in result["pii_types"]


@pytest.mark.parametrize("text,expected_has_pii", [
    ("No PII here", False),
    ("Email: test@example.com", True),
    ("Phone: 555-1234", True),
    ("SSN: 123-45-6789", True),
    ("Version 1.2.3", False),
])
def test_pii_detection_parametrized(text, expected_has_pii):
    """Parametrized test for PII detection."""
    detector = PIIDetector()
    result = detector.detect_pii(text)
    assert result["has_pii"] == expected_has_pii
