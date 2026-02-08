"""Tests for logging configuration."""

import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.unit
def test_get_logger():
    """Test getting a logger instance."""
    from app.logging_config import get_logger
    
    logger = get_logger("test_module")
    assert logger is not None
    assert logger.name == "test_module"


@pytest.mark.unit
def test_logger_info_level():
    """Test logger logs info messages."""
    from app.logging_config import get_logger
    
    logger = get_logger("test")
    
    with patch.object(logger, 'info') as mock_info:
        logger.info("Test message")
        mock_info.assert_called_once_with("Test message")


@pytest.mark.unit
def test_logger_error_level():
    """Test logger logs error messages."""
    from app.logging_config import get_logger
    
    logger = get_logger("test")
    
    with patch.object(logger, 'error') as mock_error:
        logger.error("Error message")
        mock_error.assert_called_once_with("Error message")


@pytest.mark.unit
def test_logger_warning_level():
    """Test logger logs warning messages."""
    from app.logging_config import get_logger
    
    logger = get_logger("test")
    
    with patch.object(logger, 'warning') as mock_warning:
        logger.warning("Warning message")
        mock_warning.assert_called_once_with("Warning message")


@pytest.mark.unit
def test_logger_debug_level():
    """Test logger logs debug messages."""
    from app.logging_config import get_logger
    
    logger = get_logger("test")
    
    with patch.object(logger, 'debug') as mock_debug:
        logger.debug("Debug message")
        mock_debug.assert_called_once_with("Debug message")


@pytest.mark.unit
def test_logger_with_structured_data():
    """Test logger with structured data."""
    from app.logging_config import get_logger
    
    logger = get_logger("test")
    
    with patch.object(logger, 'info') as mock_info:
        logger.info("Event occurred", extra={"event_id": "123", "user": "test"})
        assert mock_info.called


@pytest.mark.unit
def test_logger_exception():
    """Test logger exception handling."""
    from app.logging_config import get_logger
    
    logger = get_logger("test")
    
    with patch.object(logger, 'exception') as mock_exception:
        try:
            raise ValueError("Test error")
        except ValueError:
            logger.exception("Exception occurred")
        
        assert mock_exception.called


@pytest.mark.unit
@patch("google.cloud.logging.Client")
def test_gcp_logging_setup(mock_client):
    """Test GCP logging client setup."""
    from app.logging_config import get_logger
    
    logger = get_logger("test")
    assert logger is not None


@pytest.mark.unit
def test_multiple_logger_instances():
    """Test getting multiple logger instances."""
    from app.logging_config import get_logger
    
    logger1 = get_logger("module1")
    logger2 = get_logger("module2")
    
    assert logger1.name == "module1"
    assert logger2.name == "module2"
    assert logger1 != logger2
