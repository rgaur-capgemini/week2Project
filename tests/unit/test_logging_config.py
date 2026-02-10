"""
Comprehensive tests for logging_config - 100% coverage target.
"""
import pytest
from unittest.mock import patch, MagicMock
import logging

from app.logging_config import StructuredLogger, get_logger


class TestStructuredLoggerInit:
    """Test StructuredLogger initialization."""
    
    @patch('app.logging_config.cloud_logging.Client')
    def test_init_with_cloud_logging(self, mock_client_class):
        """Test initialization with Cloud Logging."""
        mock_client = MagicMock()
        mock_handler = MagicMock()
        mock_client_class.return_value = mock_client
        
        with patch('app.logging_config.CloudLoggingHandler', return_value=mock_handler):
            logger = StructuredLogger("test-project", "test-logger")
            
            # Check that logger was initialized properly
            assert hasattr(logger, 'logger')
            assert logger.logger.level == logging.INFO
            assert logger.logger.hasHandlers()
    
    @patch('app.logging_config.cloud_logging.Client')
    def test_init_cloud_logging_failure(self, mock_client_class):
        """Test initialization when Cloud Logging fails."""
        mock_client_class.side_effect = Exception("Cloud Logging unavailable")
        
        logger = StructuredLogger("test-project", "test-logger")
        
        # Should fall back to console logging
        assert logger.logger.hasHandlers()
        assert any(isinstance(h, logging.StreamHandler) for h in logger.logger.handlers)


class TestStructuredLogging:
    """Test structured logging methods."""
    
    @patch('app.logging_config.cloud_logging.Client')
    def test_info_logging(self, mock_client_class):
        """Test info logging."""
        logger = StructuredLogger("test-project", "test")
        
        with patch.object(logger.logger, 'info') as mock_info:
            logger.info("Test message", key="value")
            mock_info.assert_called_once()
    
    @patch('app.logging_config.cloud_logging.Client')
    def test_warning_logging(self, mock_client_class):
        """Test warning logging."""
        logger = StructuredLogger("test-project", "test")
        
        with patch.object(logger.logger, 'warning') as mock_warning:
            logger.warning("Warning message", code=404)
            mock_warning.assert_called_once()
    
    @patch('app.logging_config.cloud_logging.Client')
    def test_error_logging_with_exception(self, mock_client_class):
        """Test error logging with exception."""
        logger = StructuredLogger("test-project", "test")
        
        try:
            raise ValueError("Test error")
        except ValueError as e:
            with patch.object(logger.logger, 'error') as mock_error:
                logger.error("Error occurred", error=e)
                mock_error.assert_called_once()
                # Check that error details are included
                call_args = mock_error.call_args[0][0]
                assert "error_type" in call_args
                assert "ValueError" in call_args
    
    @patch('app.logging_config.cloud_logging.Client')
    def test_error_logging_without_exception(self, mock_client_class):
        """Test error logging without exception."""
        logger = StructuredLogger("test-project", "test")
        
        with patch.object(logger.logger, 'error') as mock_error:
            logger.error("Error message")
            mock_error.assert_called_once()
    
    @patch('app.logging_config.cloud_logging.Client')
    def test_critical_logging(self, mock_client_class):
        """Test critical logging."""
        logger = StructuredLogger("test-project", "test")
        
        with patch.object(logger.logger, 'critical') as mock_critical:
            logger.critical("Critical issue", severity="HIGH")
            mock_critical.assert_called_once()
    
    @patch('app.logging_config.cloud_logging.Client')
    def test_debug_logging(self, mock_client_class):
        """Test debug logging."""
        logger = StructuredLogger("test-project", "test")
        
        with patch.object(logger.logger, 'debug') as mock_debug:
            logger.debug("Debug info", details="extra")
            mock_debug.assert_called_once()


class TestGetLogger:
    """Test get_logger function."""
    
    def test_get_logger_creates_instance(self):
        """Test that get_logger creates logger instance."""
        logger = get_logger("test-module")
        
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')
    
    def test_get_logger_different_names(self):
        """Test getting loggers with different names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        
        # Both should be valid loggers
        assert logger1 is not None
        assert logger2 is not None
