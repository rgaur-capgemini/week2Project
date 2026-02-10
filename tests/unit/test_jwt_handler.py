"""
Comprehensive tests for JWTHandler - 100% coverage target.
Tests all methods, branches, edge cases, and exception paths.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta
import jwt as pyjwt

from app.auth.jwt_handler import JWTHandler


class TestJWTHandlerInit:
    """Test JWTHandler initialization."""
    
    @patch('app.auth.jwt_handler.config')
    def test_init_default_values(self, mock_config):
        """Test initialization with default values."""
        mock_config.get_secret.return_value = "test-secret"
        
        handler = JWTHandler()
        assert handler.algorithm == "HS256"
        assert handler.access_token_expire_minutes == 60
        assert handler.refresh_token_expire_days == 7
    
    @patch('app.auth.jwt_handler.config')
    @patch.dict('os.environ', {'ACCESS_TOKEN_EXPIRE_MINUTES': '30', 'REFRESH_TOKEN_EXPIRE_DAYS': '14'})
    def test_init_custom_env_values(self, mock_config):
        """Test initialization with custom environment values."""
        mock_config.get_secret.return_value = "test-secret"
        
        handler = JWTHandler()
        assert handler.access_token_expire_minutes == 30
        assert handler.refresh_token_expire_days == 14


class TestGetSecret:
    """Test _get_secret method."""
    
    @patch('app.auth.jwt_handler.config')
    def test_get_secret_success(self, mock_config):
        """Test successful secret retrieval from Secret Manager."""
        mock_config.get_secret.return_value = "test-secret-12345"
        
        handler = JWTHandler()
        secret = handler._get_secret()
        
        assert secret == "test-secret-12345"
        mock_config.get_secret.assert_called_with("chatbot-jwt-secret")
    
    @patch('app.auth.jwt_handler.config')
    @patch.dict('os.environ', {'JWT_SECRET_KEY': 'fallback-secret'})
    def test_get_secret_config_returns_none(self, mock_config):
        """Test fallback when config returns None."""
        mock_config.get_secret.return_value = None
        
        handler = JWTHandler()
        secret = handler._get_secret()
        
        assert secret == "fallback-secret"
    
    @patch('app.auth.jwt_handler.config')
    @patch.dict('os.environ', {'JWT_SECRET_KEY': 'fallback-secret'})
    def test_get_secret_exception_fallback(self, mock_config):
        """Test fallback when Secret Manager raises exception."""
        mock_config.get_secret.side_effect = Exception("Secret Manager error")
        
        handler = JWTHandler()
        secret = handler._get_secret()
        
        assert secret == "fallback-secret"
    
    @patch('app.auth.jwt_handler.config')
    @patch.dict('os.environ', {}, clear=True)
    def test_get_secret_no_config_no_env_uses_default(self, mock_config):
        """Test default secret when neither config nor env available."""
        mock_config.get_secret.return_value = None
        
        handler = JWTHandler()
        secret = handler._get_secret()
        
        assert secret == "development-secret-change-in-production"


class TestCreateAccessToken:
    """Test create_access_token method."""
    
    @patch('app.auth.jwt_handler.config')
    def test_create_access_token_basic(self, mock_config):
        """Test basic access token creation."""
        mock_config.get_secret.return_value = "test-secret"
        
        handler = JWTHandler()
        token = handler.create_access_token(
            user_id="user123",
            email="test@example.com",
            role="user"
        )
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify payload
        decoded = pyjwt.decode(token, "test-secret", algorithms=["HS256"])
        assert decoded["user_id"] == "user123"
        assert decoded["email"] == "test@example.com"
        assert decoded["role"] == "user"
        assert decoded["token_type"] == "access"
        assert "iat" in decoded
        assert "exp" in decoded
        assert "nbf" in decoded
    
    @patch('app.auth.jwt_handler.config')
    def test_create_access_token_with_additional_claims(self, mock_config):
        """Test access token with additional claims."""
        mock_config.get_secret.return_value = "test-secret"
        
        handler = JWTHandler()
        token = handler.create_access_token(
            user_id="user123",
            email="test@example.com",
            role="admin",
            additional_claims={"department": "engineering", "level": 5}
        )
        
        decoded = pyjwt.decode(token, "test-secret", algorithms=["HS256"])
        assert decoded["department"] == "engineering"
        assert decoded["level"] == 5
    
    @patch('app.auth.jwt_handler.config')
    def test_create_access_token_expiration(self, mock_config):
        """Test access token expiration is set correctly."""
        mock_config.get_secret.return_value = "test-secret"
        
        handler = JWTHandler()
        handler.access_token_expire_minutes = 30
        
        before_time = datetime.utcnow()
        token = handler.create_access_token(
            user_id="user123",
            email="test@example.com",
            role="user"
        )
        after_time = datetime.utcnow()
        
        decoded = pyjwt.decode(token, "test-secret", algorithms=["HS256"])
        exp_time = datetime.utcfromtimestamp(decoded["exp"])
        
        # Should expire in ~30 minutes
        expected_exp = before_time + timedelta(minutes=30)
        assert abs((exp_time - expected_exp).total_seconds()) < 5


class TestCreateRefreshToken:
    """Test create_refresh_token method."""
    
    @patch('app.auth.jwt_handler.config')
    def test_create_refresh_token_basic(self, mock_config):
        """Test basic refresh token creation."""
        mock_config.get_secret.return_value = "test-secret"
        
        handler = JWTHandler()
        token = handler.create_refresh_token(
            user_id="user123",
            email="test@example.com"
        )
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify payload
        decoded = pyjwt.decode(token, "test-secret", algorithms=["HS256"])
        assert decoded["user_id"] == "user123"
        assert decoded["email"] == "test@example.com"
        assert decoded["token_type"] == "refresh"
        assert "iat" in decoded
        assert "exp" in decoded
    
    @patch('app.auth.jwt_handler.config')
    def test_create_refresh_token_expiration(self, mock_config):
        """Test refresh token expiration is set correctly."""
        mock_config.get_secret.return_value = "test-secret"
        
        handler = JWTHandler()
        handler.refresh_token_expire_days = 14
        
        before_time = datetime.utcnow()
        token = handler.create_refresh_token(
            user_id="user123",
            email="test@example.com"
        )
        after_time = datetime.utcnow()
        
        decoded = pyjwt.decode(token, "test-secret", algorithms=["HS256"])
        exp_time = datetime.utcfromtimestamp(decoded["exp"])
        
        # Should expire in ~14 days
        expected_exp = before_time + timedelta(days=14)
        assert abs((exp_time - expected_exp).total_seconds()) < 5


class TestVerifyToken:
    """Test verify_token method."""
    
    @patch('app.auth.jwt_handler.config')
    def test_verify_token_valid(self, mock_config):
        """Test verifying a valid token."""
        mock_config.get_secret.return_value = "test-secret"
        
        handler = JWTHandler()
        token = handler.create_access_token(
            user_id="user123",
            email="test@example.com",
            role="user"
        )
        
        result = handler.verify_token(token)
        
        assert result == True
    
    @patch('app.auth.jwt_handler.config')
    def test_verify_token_expired(self, mock_config):
        """Test verifying an expired token."""
        mock_config.get_secret.return_value = "test-secret"
        
        handler = JWTHandler()
        handler.access_token_expire_minutes = -1  # Already expired
        
        token = handler.create_access_token(
            user_id="user123",
            email="test@example.com",
            role="user"
        )
        
        result = handler.verify_token(token)
        assert result == False
    
    @patch('app.auth.jwt_handler.config')
    def test_verify_token_invalid_signature(self, mock_config):
        """Test verifying token with invalid signature."""
        mock_config.get_secret.return_value = "test-secret"
        
        handler = JWTHandler()
        
        # Create token with different secret
        token = pyjwt.encode(
            {"user_id": "user123", "exp": datetime.utcnow() + timedelta(hours=1)},
            "different-secret",
            algorithm="HS256"
        )
        
        result = handler.verify_token(token)
        assert result == False
    
    @patch('app.auth.jwt_handler.config')
    def test_verify_token_malformed(self, mock_config):
        """Test verifying malformed token."""
        mock_config.get_secret.return_value = "test-secret"
        
        handler = JWTHandler()
        result = handler.verify_token("not-a-valid-token")
        
        assert result == False


class TestRefreshAccessToken:
    """Test refresh_access_token method."""
    
    @patch('app.auth.jwt_handler.config')
    def test_refresh_access_token_valid(self, mock_config):
        """Test refreshing with valid refresh token."""
        mock_config.get_secret.return_value = "test-secret"
        
        handler = JWTHandler()
        refresh_token = handler.create_refresh_token(
            user_id="user123",
            email="test@example.com"
        )
        
        new_access_token = handler.refresh_access_token(refresh_token, role="user")
        
        assert isinstance(new_access_token, str)
        decoded = pyjwt.decode(new_access_token, "test-secret", algorithms=["HS256"])
        assert decoded["user_id"] == "user123"
        assert decoded["email"] == "test@example.com"
        assert decoded["token_type"] == "access"
    
    @patch('app.auth.jwt_handler.config')
    def test_refresh_access_token_wrong_type(self, mock_config):
        """Test refreshing with access token (wrong type)."""
        mock_config.get_secret.return_value = "test-secret"
        
        handler = JWTHandler()
        access_token = handler.create_access_token(
            user_id="user123",
            email="test@example.com",
            role="user"
        )
        
        with pytest.raises(Exception):  # Will raise InvalidTokenError
            handler.refresh_access_token(access_token, role="user")
    
    @patch('app.auth.jwt_handler.config')
    def test_refresh_access_token_invalid(self, mock_config):
        """Test refreshing with invalid token."""
        mock_config.get_secret.return_value = "test-secret"
        
        handler = JWTHandler()
        
        with pytest.raises(Exception):  # Will raise InvalidTokenError
            handler.refresh_access_token("invalid-token", role="user")


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @patch('app.auth.jwt_handler.config')
    def test_empty_user_id(self, mock_config):
        """Test token creation with empty user_id."""
        mock_config.get_secret.return_value = "test-secret"
        
        handler = JWTHandler()
        token = handler.create_access_token(
            user_id="",
            email="test@example.com",
            role="user"
        )
        
        decoded = pyjwt.decode(token, "test-secret", algorithms=["HS256"])
        assert decoded["user_id"] == ""
    
    @patch('app.auth.jwt_handler.config')
    def test_special_characters_in_claims(self, mock_config):
        """Test token with special characters in claims."""
        mock_config.get_secret.return_value = "test-secret"
        
        handler = JWTHandler()
        token = handler.create_access_token(
            user_id="user@#$%",
            email="test+special@example.com",
            role="user"
        )
        
        decoded = pyjwt.decode(token, "test-secret", algorithms=["HS256"])
        assert decoded["user_id"] == "user@#$%"
        assert decoded["email"] == "test+special@example.com"
