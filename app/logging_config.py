"""
Production-grade Cloud Logging integration.
"""

import logging
import json
from typing import Any, Dict
from google.cloud import logging as cloud_logging
from google.cloud.logging.handlers import CloudLoggingHandler
import traceback


class StructuredLogger:
    """Structured logger with Cloud Logging integration."""
    
    def __init__(self, name: str, project_id: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        try:
            # Cloud Logging handler
            client = cloud_logging.Client(project=project_id)
            handler = CloudLoggingHandler(client, name=name)
            handler.setLevel(logging.INFO)
            
            # Console handler for local development
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            
            self.logger.addHandler(handler)
            self.logger.addHandler(console_handler)
            
        except Exception as e:
            # Fallback to console only
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            self.logger.addHandler(console_handler)
            self.logger.warning(f"Cloud Logging not available: {e}")
    
    def _structured_log(self, level: str, message: str, **kwargs):
        """Create structured log entry."""
        log_entry = {
            "message": message,
            "severity": level,
            **kwargs
        }
        
        log_method = getattr(self.logger, level.lower())
        log_method(json.dumps(log_entry))
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._structured_log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._structured_log("WARNING", message, **kwargs)
    
    def error(self, message: str, error: Exception = None, **kwargs):
        """Log error message with traceback."""
        if error:
            kwargs["error_type"] = type(error).__name__
            kwargs["error_message"] = str(error)
            kwargs["traceback"] = traceback.format_exc()
        
        self._structured_log("ERROR", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._structured_log("CRITICAL", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._structured_log("DEBUG", message, **kwargs)


def get_logger(name: str, project_id: str = None) -> StructuredLogger:
    """Get or create a structured logger."""
    from app.config import config
    project_id = project_id or config.PROJECT_ID
    return StructuredLogger(name, project_id)
