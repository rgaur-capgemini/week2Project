"""Tests for authentication modules."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.unit
def test_jwt_handler_create_token():
    """Test JWT token creation."""
    from app.auth.jwt_handler import JWTHandler
    
    handler = JWTHandler(secret_key="test-secret", algorithm="HS256")
    token = handler.create_access_token(
        data={"sub": "user123", "email": "test@example.com"}
    )
    
    assert isinstance(token, str)
    assert len(token) > 0


@pytest.mark.unit
def test_jwt_handler_decode_token():
    """Test JWT token decoding."""
    from app.auth.jwt_handler import JWTHandler
    
    handler = JWTHandler(secret_key="test-secret", algorithm="HS256")
    token = handler.create_access_token(
        data={"sub": "user123", "email": "test@example.com"}
    )
    
    payload = handler.decode_token(token)
    assert payload["sub"] == "user123"
    assert payload["email"] == "test@example.com"


@pytest.mark.unit
def test_jwt_handler_expired_token():
    """Test JWT handler detects expired tokens."""
    from app.auth.jwt_handler import JWTHandler
    import jwt
    
    handler = JWTHandler(secret_key="test-secret", algorithm="HS256")
    token = handler.create_access_token(
        data={"sub": "user123"},
        expires_delta=timedelta(seconds=-1)  # Already expired
    )
    
    with pytest.raises(jwt.ExpiredSignatureError):
        handler.decode_token(token)


@pytest.mark.unit
def test_jwt_handler_invalid_token():
    """Test JWT handler detects invalid tokens."""
    from app.auth.jwt_handler import JWTHandler
    import jwt
    
    handler = JWTHandler(secret_key="test-secret", algorithm="HS256")
    
    with pytest.raises(jwt.InvalidTokenError):
        handler.decode_token("invalid.token.here")


@pytest.mark.unit
def test_rbac_manager_initialization():
    """Test RBAC manager initialization."""
    from app.auth.rbac import RBACManager
    
    manager = RBACManager(admin_emails=["admin@example.com"])
    assert "admin@example.com" in manager.admin_emails


@pytest.mark.unit
def test_rbac_manager_admin_role():
    """Test RBAC manager assigns admin role to admin emails."""
    from app.auth.rbac import RBACManager, Role
    
    manager = RBACManager(admin_emails=["admin@example.com"])
    role = manager.get_role("admin@example.com")
    assert role == Role.ADMIN


@pytest.mark.unit
def test_rbac_manager_user_role():
    """Test RBAC manager assigns user role to non-admin emails."""
    from app.auth.rbac import RBACManager, Role
    
    manager = RBACManager(admin_emails=["admin@example.com"])
    role = manager.get_role("user@example.com")
    assert role == Role.USER


@pytest.mark.unit
def test_rbac_manager_check_permission_admin():
    """Test RBAC manager grants all permissions to admin."""
    from app.auth.rbac import RBACManager, Permission
    
    manager = RBACManager(admin_emails=["admin@example.com"])
    
    # Admin should have all permissions
    assert manager.check_permission("admin@example.com", Permission.READ_DATA)
    assert manager.check_permission("admin@example.com", Permission.WRITE_DATA)
    assert manager.check_permission("admin@example.com", Permission.DELETE_DATA)
    assert manager.check_permission("admin@example.com", Permission.MANAGE_USERS)


@pytest.mark.unit
def test_rbac_manager_check_permission_user():
    """Test RBAC manager grants limited permissions to users."""
    from app.auth.rbac import RBACManager, Permission
    
    manager = RBACManager(admin_emails=["admin@example.com"])
    
    # User should have read/write but not delete/manage
    assert manager.check_permission("user@example.com", Permission.READ_DATA)
    assert manager.check_permission("user@example.com", Permission.WRITE_DATA)
    assert not manager.check_permission("user@example.com", Permission.DELETE_DATA)
    assert not manager.check_permission("user@example.com", Permission.MANAGE_USERS)


@pytest.mark.unit
def test_rbac_get_permissions():
    """Test RBAC manager returns list of permissions."""
    from app.auth.rbac import RBACManager
    
    manager = RBACManager(admin_emails=["admin@example.com"])
    
    admin_perms = manager.get_permissions("admin@example.com")
    assert len(admin_perms) > 0
    
    user_perms = manager.get_permissions("user@example.com")
    assert len(user_perms) > 0
    assert len(admin_perms) > len(user_perms)


@pytest.mark.unit
@patch("google.oauth2.id_token.verify_oauth2_token")
def test_oidc_verify_google_token(mock_verify):
    """Test OIDC Google token verification."""
    from app.auth.oidc import verify_google_token
    
    mock_verify.return_value = {
        "sub": "google-user-id-123",
        "email": "test@example.com",
        "name": "Test User",
        "email_verified": True
    }
    
    user_info = verify_google_token("test-token")
    
    assert user_info["sub"] == "google-user-id-123"
    assert user_info["email"] == "test@example.com"
    assert user_info["email_verified"] is True


@pytest.mark.unit
@patch("google.oauth2.id_token.verify_oauth2_token")
def test_oidc_invalid_token(mock_verify):
    """Test OIDC handles invalid tokens."""
    from app.auth.oidc import verify_google_token
    from google.auth.exceptions import GoogleAuthError
    
    mock_verify.side_effect = GoogleAuthError("Invalid token")
    
    with pytest.raises(Exception):
        verify_google_token("invalid-token")


@pytest.mark.unit
def test_rbac_role_enum():
    """Test Role enum values."""
    from app.auth.rbac import Role
    
    assert hasattr(Role, "ADMIN")
    assert hasattr(Role, "USER")
    assert hasattr(Role, "GUEST")


@pytest.mark.unit
def test_rbac_permission_enum():
    """Test Permission enum values."""
    from app.auth.rbac import Permission
    
    assert hasattr(Permission, "READ_DATA")
    assert hasattr(Permission, "WRITE_DATA")
    assert hasattr(Permission, "DELETE_DATA")
    assert hasattr(Permission, "MANAGE_USERS")
