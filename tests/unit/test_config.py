"""
Unit tests for configuration module.
"""
import pytest
from unittest.mock import patch, MagicMock
import os

from app.config import Config


class TestConfigInit:
    """Test Config class initialization."""
    
    def test_init_with_defaults(self):
        """Test initialization with default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            
            assert config.PROJECT_ID == "btoproject-486405"
            assert config.REGION == "us-central1"
            assert config.ENVIRONMENT == "production"
    
    def test_init_with_env_vars(self):
        """Test initialization with environment variables."""
        with patch.dict(os.environ, {
            "PROJECT_ID": "test-project",
            "REGION": "us-west1",
            "ENVIRONMENT": "development"
        }):
            config = Config()
            
            assert config.PROJECT_ID == "test-project"
            assert config.REGION == "us-west1"
            assert config.ENVIRONMENT == "development"
    
    @patch('app.config.SECRET_MANAGER_AVAILABLE', True)
    @patch('app.config.SecretManagerServiceClient')
    def test_init_with_secret_manager(self, mock_sm_class):
        """Test initialization with Secret Manager available."""
        mock_client = MagicMock()
        mock_sm_class.return_value = mock_client
        
        config = Config()
        
        assert config.secret_client == mock_client
    
    @patch('app.config.SECRET_MANAGER_AVAILABLE', False)
    def test_init_without_secret_manager(self):
        """Test initialization without Secret Manager."""
        config = Config()
        
        assert config.secret_client is None


class TestGetSecret:
    """Test get_secret method."""
    
    @patch('app.config.SECRET_MANAGER_AVAILABLE', True)
    @patch('app.config.SecretManagerServiceClient')
    def test_get_secret_success(self, mock_sm_class):
        """Test getting secret successfully."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.payload.data.decode.return_value = "secret-value"
        mock_client.access_secret_version.return_value = mock_response
        mock_sm_class.return_value = mock_client
        
        config = Config()
        result = config.get_secret("test-secret")
        
        assert result == "secret-value"
    
    @patch('app.config.SECRET_MANAGER_AVAILABLE', False)
    def test_get_secret_not_available(self):
        """Test get_secret when Secret Manager not available."""
        with patch.dict(os.environ, {"test-secret": "env-value"}):
            config = Config()
            result = config.get_secret("test-secret")
            
            assert result == "env-value"
    
    @patch('app.config.SECRET_MANAGER_AVAILABLE', True)
    @patch('app.config.SecretManagerServiceClient')
    def test_get_secret_error_fallback(self, mock_sm_class):
        """Test get_secret fallback to env var on error."""
        mock_client = MagicMock()
        mock_client.access_secret_version.side_effect = Exception("Secret not found")
        mock_sm_class.return_value = mock_client
        
        with patch.dict(os.environ, {"test-secret": "fallback-value"}):
            config = Config()
            result = config.get_secret("test-secret")
            
            assert result == "fallback-value"


class TestValidate:
    """Test validate method."""
    
    def test_validate_success(self):
        """Test validation with valid config."""
        config = Config()
        result = config.validate()
        
        assert result["valid"] is True
        assert len(result["issues"]) == 0
        assert "config" in result
    
    def test_validate_missing_project_id(self):
        """Test validation with missing PROJECT_ID."""
        with patch.dict(os.environ, {"PROJECT_ID": ""}, clear=True):
            config = Config()
            config.PROJECT_ID = ""
            result = config.validate()
            
            assert result["valid"] is False
            assert "PROJECT_ID is not set" in result["issues"]
    
    def test_validate_missing_vertex_index(self):
        """Test validation with missing VERTEX_INDEX_ID."""
        config = Config()
        config.VERTEX_INDEX_ID = ""
        result = config.validate()
        
        assert result["valid"] is False
        assert "VERTEX_INDEX_ID is not set" in result["issues"]
    
    def test_validate_missing_endpoint(self):
        """Test validation with missing VERTEX_INDEX_ENDPOINT."""
        config = Config()
        config.VERTEX_INDEX_ENDPOINT = ""
        result = config.validate()
        
        assert result["valid"] is False
        assert "VERTEX_INDEX_ENDPOINT is not set" in result["issues"]


class TestToDict:
    """Test to_dict method."""
    
    def test_to_dict_exports_config(self):
        """Test that to_dict exports configuration."""
        config = Config()
        result = config.to_dict()
        
        assert isinstance(result, dict)
        assert "PROJECT_ID" in result
        assert "REGION" in result
        assert "MODEL_VARIANT" in result
    
    def test_to_dict_excludes_secrets(self):
        """Test that to_dict excludes sensitive data."""
        config = Config()
        result = config.to_dict()
        
        # Should not contain secret_client or passwords
        assert "secret_client" not in result
        assert "password" not in str(result).lower() or result.get("REDIS_PASSWORD") == "***"


class TestConfigModule:
    """Test config module-level attributes."""
    
    def test_config_loads_defaults(self):
        """Test that config module loads."""
        from app.config import config
        
        assert config is not None
        assert hasattr(config, 'PROJECT_ID')
    
    def test_admin_emails(self):
        """Test admin emails configuration."""
        from app.config import config
        
        assert hasattr(config, 'ADMIN_EMAILS')
        assert isinstance(config.ADMIN_EMAILS, list)
