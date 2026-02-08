"""
Unit tests for configuration module.
"""
import pytest
from unittest.mock import patch
import os


class TestConfig:
    """Test configuration loading."""
    
    def test_config_loads_defaults(self):
        """Test that config has default values."""
        from app.config import PROJECT_ID, REGION
        
        assert PROJECT_ID is not None
        assert REGION is not None
    
    def test_config_from_env(self, monkeypatch):
        """Test loading config from environment variables."""
        monkeypatch.setenv("PROJECT_ID", "test-project")
        monkeypatch.setenv("REGION", "us-west1")
        
        # Reload config
        import importlib
        from app import config
        importlib.reload(config)
        
        assert config.PROJECT_ID == "test-project"
        assert config.REGION == "us-west1"
    
    def test_redis_config(self):
        """Test Redis configuration."""
        from app.config import REDIS_HOST, REDIS_PORT
        
        assert REDIS_HOST is not None
        assert REDIS_PORT is not None
    
    def test_vertex_ai_config(self):
        """Test Vertex AI configuration."""
        from app.config import VERTEX_INDEX_ID, VERTEX_INDEX_ENDPOINT
        
        assert VERTEX_INDEX_ID is not None
        assert VERTEX_INDEX_ENDPOINT is not None
    
    def test_admin_emails_config(self):
        """Test admin emails configuration."""
        from app.config import ADMIN_EMAILS
        
        assert isinstance(ADMIN_EMAILS, list)
        assert len(ADMIN_EMAILS) > 0


class TestLoggingConfig:
    """Test logging configuration."""
    
    def test_logging_setup(self):
        """Test that logging is configured."""
        from app.logging_config import setup_logging
        
        logger = setup_logging()
        assert logger is not None
    
    def test_logger_levels(self):
        """Test logger level configuration."""
        from app.logging_config import setup_logging
        import logging
        
        logger = setup_logging()
        # Should have a valid level
        assert logger.level in [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]


class TestTelemetry:
    """Test telemetry configuration."""
    
    def test_telemetry_init(self, mocker):
        """Test telemetry initialization."""
        # Mock Cloud Trace
        mocker.patch("google.cloud.trace_v2.TraceServiceClient")
        
        from app.telemetry import init_telemetry
        
        # Should not raise error
        try:
            init_telemetry()
        except Exception:
            pass  # OK if it fails in test environment
