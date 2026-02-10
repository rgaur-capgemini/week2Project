"""
Comprehensive unit tests for JWT handler.
Tests token creation, validation, and refresh.
"""
import pytest
import jwt
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from app.auth.jwt_handler import JWTHandler


class TestJWTHandler:
    """Test JWT token generation and validation with ≥80% coverage."""
    
    @pytest.fixture
    def jwt_handler(self):
        """Create JWT handler with mocked secret."""
        with patch('app.auth.jwt_handler.config') as mock_config:
            mock_config.get_secret.return_value = "test-secret-key-12345"
            handler = JWTHandler()
            return handler
    
    @pytest.fixture
    def mock_config(self):
        """Mock config for secret management."""
        with patch('app.auth.jwt_handler.config') as mock:
            mock.get_secret.return_value = "test-secret-key-12345"
            yield mock
    
    def test_init_default_values(self, jwt_handler):
        """Test initialization with default values."""
        assert jwt_handler.algorithm == "HS256"
        assert jwt_handler.access_token_expire_minutes == 60
        assert jwt_handler.refresh_token_expire_days == 7
    
    def test_init_custom_env_values(self, mock_config):
        """Test initialization with custom environment values."""
        with patch.dict('os.environ', {
            'ACCESS_TOKEN_EXPIRE_MINUTES': '30',
            'REFRESH_TOKEN_EXPIRE_DAYS': '14'
        }):
            handler = JWTHandler()
            assert handler.access_token_expire_minutes == 30
            assert handler.refresh_token_expire_days == 14
    
    def test_get_secret_success(self, jwt_handler, mock_config):
        """Test successful secret retrieval."""
        secret = jwt_handler._get_secret()
        assert secret == "test-secret-key-12345"
        mock_config.get_secret.assert_called_once_with("chatbot-jwt-secret")
    
    def test_get_secret_failure_fallback(self, jwt_handler):
        """Test fallback when secret retrieval fails."""
        with patch('app.auth.jwt_handler.config') as mock_config:
            mock_config.get_secret.side_effect = Exception("Secret Manager error")
            with patch.dict('os.environ', {'JWT_SECRET_KEY': 'fallback-secret'}):
                secret = jwt_handler._get_secret()
                assert secret == 'fallback-secret'
    
    def test_get_secret_no_config_no_env(self, jwt_handler):
        """Test fallback to default when no secret configured."""
        with patch('app.auth.jwt_handler.config') as mock_config:
            mock_config.get_secret.return_value = None
            with patch.dict('os.environ', {}, clear=True):
                with pytest.raises(RuntimeError, match="JWT secret not configured"):
                    jwt_handler._get_secret()
    
    def test_create_access_token_basic(self, jwt_handler):
        """Test basic access token creation."""
        token = jwt_handler.create_access_token(
            user_id="user123",
            email="test@example.com",
            role="user"
        )
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify
        secret = jwt_handler._get_secret()
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        
        assert payload["user_id"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "user"
        assert payload["token_type"] == "access"
        assert "iat" in payload
        assert "exp" in payload
        assert "nbf" in payload
    
    def test_create_access_token_with_additional_claims(self, jwt_handler):
        """Test token creation with additional claims."""
        additional_claims = {
            "department": "engineering",
            "level": "senior"
        }
        
        token = jwt_handler.create_access_token(
            user_id="user123",
            email="test@example.com",
            role="admin",
            additional_claims=additional_claims
        )
        
        secret = jwt_handler._get_secret()
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        
        assert payload["department"] == "engineering"
        assert payload["level"] == "senior"
        assert payload["role"] == "admin"
    
    def test_create_access_token_expiration(self, jwt_handler):
        """Test that token has correct expiration time."""
        before = datetime.utcnow()
        token = jwt_handler.create_access_token(
            user_id="user123",
            email="test@example.com",
            role="user"
        )
        after = datetime.utcnow()
        
        secret = jwt_handler._get_secret()
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        
        exp_time = datetime.fromtimestamp(payload["exp"])
        expected_exp = before + timedelta(minutes=jwt_handler.access_token_expire_minutes)
        
        # Allow 1 minute tolerance
        assert abs((exp_time - expected_exp).total_seconds()) < 60
    
    def test_create_refresh_token_basic(self, jwt_handler):
        """Test refresh token creation."""
        token = jwt_handler.create_refresh_token(
            user_id="user123",
            email="test@example.com"
        )
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        secret = jwt_handler._get_secret()
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        
        assert payload["user_id"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["token_type"] == "refresh"
    
    def test_create_refresh_token_expiration(self, jwt_handler):
        """Test refresh token has longer expiration."""
        token = jwt_handler.create_refresh_token(
            user_id="user123",
            email="test@example.com"
        )
        
        secret = jwt_handler._get_secret()
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        
        exp_time = datetime.fromtimestamp(payload["exp"])
        now = datetime.utcnow()
        
        # Should expire in approximately 7 days
        time_diff = (exp_time - now).total_seconds()
        expected_seconds = jwt_handler.refresh_token_expire_days * 24 * 60 * 60
        
        # Allow 1 hour tolerance
        assert abs(time_diff - expected_seconds) < 3600
    
    def test_verify_token_valid(self, jwt_handler):
        """Test verification of valid token."""
        token = jwt_handler.create_access_token(
            user_id="user123",
            email="test@example.com",
            role="user"
        )
        
        result = jwt_handler.verify_token(token)
        assert result is not None
        assert result["user_id"] == "user123"
    
    def test_verify_token_expired(self, jwt_handler):
        """Test verification of expired token."""
        # Create token that expires immediately
        jwt_handler.access_token_expire_minutes = -1
        token = jwt_handler.create_access_token(
            user_id="user123",
            email="test@example.com",
            role="user"
        )
        
        # Wait a moment to ensure expiration
        import time
        time.sleep(1)
        
        result = jwt_handler.verify_token(token)
        assert result is None
    
    def test_verify_token_invalid_signature(self, jwt_handler):
        """Test verification of token with invalid signature."""
        token = jwt_handler.create_access_token(
            user_id="user123",
            email="test@example.com",
            role="user"
        )
        
        # Tamper with token
        tampered_token = token[:-10] + "tampered123"
        
        result = jwt_handler.verify_token(tampered_token)
        assert result is None
    
    def test_verify_token_malformed(self, jwt_handler):
        """Test verification of malformed token."""
        result = jwt_handler.verify_token("not.a.valid.token")
        assert result is None
    
    def test_verify_token_wrong_algorithm(self, jwt_handler):
        """Test verification rejects token with wrong algorithm."""
        # Create token with different algorithm
        secret = jwt_handler._get_secret()
        payload = {"user_id": "user123", "exp": datetime.utcnow() + timedelta(hours=1)}
        token = jwt.encode(payload, secret, algorithm="HS512")
        
        result = jwt_handler.verify_token(token)
        assert result is None
    
    def test_decode_token_success(self, jwt_handler):
        """Test decoding valid token."""
        token = jwt_handler.create_access_token(
            user_id="user123",
            email="test@example.com",
            role="admin"
        )
        
        payload = jwt_handler.decode_token(token)
        
        assert payload["user_id"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "admin"
    
    def test_decode_token_expired(self, jwt_handler):
        """Test decoding expired token raises exception."""
        jwt_handler.access_token_expire_minutes = -1
        token = jwt_handler.create_access_token(
            user_id="user123",
            email="test@example.com",
            role="user"
        )
        
        import time
        time.sleep(1)
        
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt_handler.decode_token(token)
    
    def test_decode_token_invalid(self, jwt_handler):
        """Test decoding invalid token raises exception."""
        with pytest.raises(jwt.InvalidTokenError):
            jwt_handler.decode_token("invalid.token.here")
    
    def test_refresh_access_token_success(self, jwt_handler):
        """Test refreshing access token with valid refresh token."""
        refresh_token = jwt_handler.create_refresh_token(
            user_id="user123",
            email="test@example.com"
        )
        
        new_access_token = jwt_handler.refresh_access_token(
            refresh_token=refresh_token,
            role="user"
        )
        
        assert new_access_token is not None
        secret = jwt_handler._get_secret()
        payload = jwt.decode(new_access_token, secret, algorithms=["HS256"])
        assert payload["user_id"] == "user123"
        assert payload["token_type"] == "access"
    
    def test_refresh_access_token_invalid_type(self, jwt_handler):
        """Test that access token cannot be used for refresh."""
        access_token = jwt_handler.create_access_token(
            user_id="user123",
            email="test@example.com",
            role="user"
        )
        
        result = jwt_handler.refresh_access_token(
            refresh_token=access_token,
            role="user"
        )
        
        assert result is None
    
    def test_refresh_access_token_expired_refresh_token(self, jwt_handler):
        """Test that expired refresh token cannot refresh."""
        jwt_handler.refresh_token_expire_days = -1
        refresh_token = jwt_handler.create_refresh_token(
            user_id="user123",
            email="test@example.com"
        )
        
        import time
        time.sleep(1)
        
        result = jwt_handler.refresh_access_token(
            refresh_token=refresh_token,
            role="user"
        )
        
        assert result is None
    
    def test_token_not_before_claim(self, jwt_handler):
        """Test that token includes not-before (nbf) claim."""
        token = jwt_handler.create_access_token(
            user_id="user123",
            email="test@example.com",
            role="user"
        )
        
        secret = jwt_handler._get_secret()
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        
        assert "nbf" in payload
        nbf_time = datetime.fromtimestamp(payload["nbf"])
        now = datetime.utcnow()
        
        # nbf should be very recent (within 1 minute)
        assert abs((now - nbf_time).total_seconds()) < 60
    
    @pytest.mark.parametrize("role", ["user", "admin", "service_account"])
    def test_create_token_various_roles(self, jwt_handler, role):
        """Test token creation for different roles."""
        token = jwt_handler.create_access_token(
            user_id=f"user_{role}",
            email=f"{role}@example.com",
            role=role
        )
        
        secret = jwt_handler._get_secret()
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        assert payload["role"] == role
    
    def test_token_reuse_prevention(self, jwt_handler):
        """Test that each token is unique (different iat)."""
        token1 = jwt_handler.create_access_token(
            user_id="user123",
            email="test@example.com",
            role="user"
        )
        
        import time
        time.sleep(1)
        
        token2 = jwt_handler.create_access_token(
            user_id="user123",
            email="test@example.com",
            role="user"
        )
        
        assert token1 != token2
        
        secret = jwt_handler._get_secret()
        payload1 = jwt.decode(token1, secret, algorithms=["HS256"])
        payload2 = jwt.decode(token2, secret, algorithms=["HS256"])
        
        assert payload1["iat"] != payload2["iat"]
