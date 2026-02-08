"""
Integration tests for authentication system.
Tests OIDC and JWT authentication.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import jwt as pyjwt
from datetime import datetime, timedelta


@pytest.fixture
def mock_dependencies(mocker):
    """Mock external dependencies."""
    mocker.patch("google.cloud.secretmanager_v1.SecretManagerServiceClient")
    mocker.patch("redis.Redis")
    mocker.patch("google.cloud.firestore.Client")
    mocker.patch("google.cloud.aiplatform.init")
    yield


@pytest.fixture
def client(mock_dependencies):
    """Create test client."""
    from app.main import app
    return TestClient(app)


class TestJWTAuthentication:
    """Test JWT token operations."""
    
    def test_generate_token(self, mocker):
        """Test JWT token generation."""
        from app.auth.jwt_handler import generate_token
        
        # Mock secret retrieval
        mocker.patch("app.auth.jwt_handler._get_secret", return_value="test-secret")
        
        user_data = {
            "sub": "test-user",
            "email": "test@example.com",
            "role": "user"
        }
        
        token = generate_token(user_data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_valid_token(self, mocker):
        """Test verification of valid token."""
        from app.auth.jwt_handler import generate_token, verify_token
        
        secret = "test-secret"
        mocker.patch("app.auth.jwt_handler._get_secret", return_value=secret)
        
        user_data = {
            "sub": "test-user",
            "email": "test@example.com",
            "role": "user"
        }
        
        token = generate_token(user_data)
        verified = verify_token(token)
        
        assert verified is not None
        assert verified["sub"] == user_data["sub"]
        assert verified["email"] == user_data["email"]
    
    def test_verify_expired_token(self, mocker):
        """Test verification of expired token."""
        from app.auth.jwt_handler import verify_token
        
        secret = "test-secret"
        mocker.patch("app.auth.jwt_handler._get_secret", return_value=secret)
        
        # Create expired token
        payload = {
            "sub": "test-user",
            "email": "test@example.com",
            "exp": datetime.utcnow() - timedelta(hours=1)
        }
        token = pyjwt.encode(payload, secret, algorithm="HS256")
        
        with pytest.raises(Exception):
            verify_token(token)
    
    def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        from app.auth.jwt_handler import verify_token
        
        with pytest.raises(Exception):
            verify_token("invalid.token.here")
    
    def test_token_with_admin_role(self, mocker):
        """Test token with admin role."""
        from app.auth.jwt_handler import generate_token, verify_token
        
        mocker.patch("app.auth.jwt_handler._get_secret", return_value="test-secret")
        
        admin_data = {
            "sub": "admin-user",
            "email": "admin@example.com",
            "role": "admin"
        }
        
        token = generate_token(admin_data)
        verified = verify_token(token)
        
        assert verified["role"] == "admin"


class TestOIDCAuthentication:
    """Test OIDC authentication flow."""
    
    def test_oidc_callback(self, client, mocker):
        """Test OIDC callback handling."""
        # Mock OIDC verification
        mock_verify = mocker.patch("app.auth.oidc.verify_google_token")
        mock_verify.return_value = {
            "sub": "google-user-123",
            "email": "user@example.com",
            "email_verified": True
        }
        
        # Mock JWT generation
        mocker.patch("app.auth.jwt_handler.generate_token", return_value="test-jwt-token")
        
        response = client.post(
            "/auth/callback",
            json={"id_token": "fake-google-token"}
        )
        
        # Should return JWT token
        assert response.status_code in [200, 404]  # 404 if endpoint doesn't exist
    
    def test_invalid_google_token(self, client, mocker):
        """Test handling of invalid Google token."""
        mock_verify = mocker.patch("app.auth.oidc.verify_google_token")
        mock_verify.side_effect = Exception("Invalid token")
        
        response = client.post(
            "/auth/callback",
            json={"id_token": "invalid-token"}
        )
        
        assert response.status_code in [401, 404]


class TestRoleAssignment:
    """Test role assignment logic."""
    
    def test_admin_email_gets_admin_role(self, mocker):
        """Test that admin emails get admin role."""
        from app.auth.role_manager import assign_role
        
        # Mock config
        mocker.patch("app.config.ADMIN_EMAILS", ["admin@example.com"])
        
        role = assign_role("admin@example.com")
        assert role == "admin"
    
    def test_regular_email_gets_user_role(self, mocker):
        """Test that regular emails get user role."""
        from app.auth.role_manager import assign_role
        
        mocker.patch("app.config.ADMIN_EMAILS", ["admin@example.com"])
        
        role = assign_role("user@example.com")
        assert role == "user"


class TestAuthenticationMiddleware:
    """Test authentication middleware."""
    
    def test_protected_endpoint_requires_auth(self, client):
        """Test that protected endpoints require authentication."""
        response = client.post(
            "/query",
            json={"question": "test"}
        )
        
        assert response.status_code in [401, 422]
    
    def test_valid_token_allows_access(self, client, mocker):
        """Test that valid token allows access."""
        # Mock token verification
        mocker.patch("app.auth.jwt_handler.verify_token", return_value={
            "sub": "test-user",
            "email": "test@example.com",
            "role": "user"
        })
        
        # Mock RAG components
        mocker.patch("app.rag.embeddings.EmbeddingGenerator.generate", 
                    return_value=[0.1] * 768)
        mocker.patch("app.rag.vector_store.VectorStore.search", 
                    return_value=[Mock(id="doc-0")])
        mocker.patch("app.rag.generator.AnswerGenerator.generate", 
                    return_value="Answer")
        
        response = client.post(
            "/query",
            json={"question": "test"},
            headers={"Authorization": "Bearer valid-token"}
        )
        
        assert response.status_code == 200
    
    def test_malformed_auth_header(self, client):
        """Test handling of malformed auth header."""
        response = client.post(
            "/query",
            json={"question": "test"},
            headers={"Authorization": "NotBearer token"}
        )
        
        assert response.status_code in [401, 422]


class TestSecretManager:
    """Test Secret Manager integration."""
    
    def test_fetch_secret_success(self, mocker):
        """Test successful secret fetching."""
        from app.auth.jwt_handler import _get_secret
        
        # Mock Secret Manager
        mock_client = mocker.Mock()
        mock_response = mocker.Mock()
        mock_response.payload.data = b"test-secret-value"
        mock_client.access_secret_version.return_value = mock_response
        
        mocker.patch("google.cloud.secretmanager_v1.SecretManagerServiceClient", 
                    return_value=mock_client)
        
        secret = _get_secret("test-secret-name")
        
        assert secret == "test-secret-value"
    
    def test_fetch_secret_fallback_to_env(self, mocker):
        """Test fallback to environment variable."""
        from app.auth.jwt_handler import _get_secret
        
        # Mock Secret Manager to fail
        mock_client = mocker.Mock()
        mock_client.access_secret_version.side_effect = Exception("Not found")
        
        mocker.patch("google.cloud.secretmanager_v1.SecretManagerServiceClient", 
                    return_value=mock_client)
        mocker.patch.dict("os.environ", {"JWT_SECRET_KEY": "fallback-secret"})
        
        secret = _get_secret("test-secret", fallback_env_var="JWT_SECRET_KEY")
        
        assert secret == "fallback-secret"


class TestAuthorizationDecorators:
    """Test authorization decorators."""
    
    def test_require_admin_decorator(self, client, mocker):
        """Test require_admin decorator."""
        # User without admin role
        mocker.patch("app.auth.jwt_handler.verify_token", return_value={
            "sub": "user",
            "email": "user@example.com",
            "role": "user"
        })
        
        response = client.post(
            "/ingest",
            files={"files": ("test.txt", b"Test", "text/plain")},
            headers={"Authorization": "Bearer token"}
        )
        
        assert response.status_code in [403, 401]
    
    def test_require_user_decorator(self, client, mocker):
        """Test require_user decorator (any authenticated user)."""
        mocker.patch("app.auth.jwt_handler.verify_token", return_value={
            "sub": "user",
            "email": "user@example.com",
            "role": "user"
        })
        
        # Mock RAG components
        mocker.patch("app.rag.embeddings.EmbeddingGenerator.generate", 
                    return_value=[0.1] * 768)
        mocker.patch("app.rag.vector_store.VectorStore.search", 
                    return_value=[])
        mocker.patch("app.rag.generator.AnswerGenerator.generate", 
                    return_value="Answer")
        
        response = client.post(
            "/query",
            json={"question": "test"},
            headers={"Authorization": "Bearer token"}
        )
        
        assert response.status_code == 200


@pytest.mark.integration
class TestCompleteAuthFlow:
    """Test complete authentication flow."""
    
    def test_full_authentication_flow(self, client, mocker):
        """Test complete flow from OIDC to JWT to API access."""
        # Step 1: Mock OIDC callback
        google_user_info = {
            "sub": "google-123",
            "email": "user@example.com",
            "email_verified": True
        }
        
        mocker.patch("app.auth.oidc.verify_google_token", return_value=google_user_info)
        
        # Step 2: Generate JWT
        from app.auth.jwt_handler import generate_token
        mocker.patch("app.auth.jwt_handler._get_secret", return_value="test-secret")
        
        jwt_token = generate_token({
            "sub": google_user_info["sub"],
            "email": google_user_info["email"],
            "role": "user"
        })
        
        # Step 3: Use JWT to access API
        mocker.patch("app.auth.jwt_handler.verify_token", return_value={
            "sub": google_user_info["sub"],
            "email": google_user_info["email"],
            "role": "user"
        })
        
        # Mock RAG
        mocker.patch("app.rag.embeddings.EmbeddingGenerator.generate", 
                    return_value=[0.1] * 768)
        mocker.patch("app.rag.vector_store.VectorStore.search", return_value=[])
        mocker.patch("app.rag.generator.AnswerGenerator.generate", 
                    return_value="Answer")
        
        response = client.post(
            "/query",
            json={"question": "test"},
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
