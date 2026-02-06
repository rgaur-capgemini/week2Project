"""
Comprehensive test suite for authentication and authorization.
Achieves high code coverage for auth module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from app.auth.oidc import GoogleOIDCValidator, get_current_user, get_optional_user
from app.auth.rbac import RBACManager, Role, Permission, rbac_manager, require_permission, require_role


class TestGoogleOIDCValidator:
    """Test OIDC token validation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.validator = GoogleOIDCValidator(client_ids=["test-client-id"])
    
    @patch('app.auth.oidc.id_token.verify_oauth2_token')
    def test_verify_valid_token(self, mock_verify):
        """Test successful token verification."""
        mock_verify.return_value = {
            'iss': 'accounts.google.com',
            'aud': 'test-client-id',
            'sub': '12345',
            'email': 'test@example.com',
            'email_verified': True,
            'name': 'Test User',
            'picture': 'https://example.com/photo.jpg'
        }
        
        result = self.validator.verify_token('valid-token')
        
        assert result['email'] == 'test@example.com'
        assert result['sub'] == '12345'
        assert result['email_verified'] is True
    
    @patch('app.auth.oidc.id_token.verify_oauth2_token')
    def test_verify_invalid_issuer(self, mock_verify):
        """Test token with invalid issuer."""
        mock_verify.return_value = {
            'iss': 'invalid-issuer.com',
            'sub': '12345',
            'email': 'test@example.com',
            'email_verified': True
        }
        
        with pytest.raises(HTTPException) as exc_info:
            self.validator.verify_token('invalid-token')
        
        assert exc_info.value.status_code == 401
    
    @patch('app.auth.oidc.id_token.verify_oauth2_token')
    def test_verify_unverified_email(self, mock_verify):
        """Test token with unverified email."""
        mock_verify.return_value = {
            'iss': 'accounts.google.com',
            'sub': '12345',
            'email': 'test@example.com',
            'email_verified': False
        }
        
        with pytest.raises(HTTPException) as exc_info:
            self.validator.verify_token('invalid-token')
        
        assert exc_info.value.status_code == 401
    
    @patch('app.auth.oidc.id_token.verify_oauth2_token')
    def test_token_caching(self, mock_verify):
        """Test that tokens are cached."""
        mock_verify.return_value = {
            'iss': 'accounts.google.com',
            'aud': 'test-client-id',
            'sub': '12345',
            'email': 'test@example.com',
            'email_verified': True
        }
        
        # First call
        self.validator.verify_token('test-token')
        # Second call should use cache
        self.validator.verify_token('test-token')
        
        # Verify called only once due to caching
        assert mock_verify.call_count == 1


class TestRBACManager:
    """Test role-based access control."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.rbac = RBACManager()
    
    def test_assign_role(self):
        """Test role assignment."""
        self.rbac.assign_role('user@example.com', Role.ADMIN)
        role = self.rbac.get_user_role('user@example.com')
        assert role == Role.ADMIN
    
    def test_get_default_role(self):
        """Test default role for new user."""
        role = self.rbac.get_user_role('newuser@example.com')
        assert role == Role.USER
    
    def test_admin_has_all_permissions(self):
        """Test that admin has all permissions."""
        self.rbac.assign_role('admin@example.com', Role.ADMIN)
        
        for permission in Permission:
            assert self.rbac.has_permission('admin@example.com', permission)
    
    def test_user_has_limited_permissions(self):
        """Test that regular user has limited permissions."""
        self.rbac.assign_role('user@example.com', Role.USER)
        
        # Should have query permission
        assert self.rbac.has_permission('user@example.com', Permission.QUERY_RAG)
        
        # Should not have admin permissions
        assert not self.rbac.has_permission('user@example.com', Permission.VIEW_ANALYTICS)
        assert not self.rbac.has_permission('user@example.com', Permission.MANAGE_USERS)
    
    def test_viewer_has_minimal_permissions(self):
        """Test that viewer has minimal permissions."""
        self.rbac.assign_role('viewer@example.com', Role.VIEWER)
        
        # Should have read permissions
        assert self.rbac.has_permission('viewer@example.com', Permission.QUERY_RAG)
        assert self.rbac.has_permission('viewer@example.com', Permission.VIEW_DOCUMENT)
        
        # Should not have write permissions
        assert not self.rbac.has_permission('viewer@example.com', Permission.UPLOAD_DOCUMENT)
        assert not self.rbac.has_permission('viewer@example.com', Permission.DELETE_DOCUMENT)
    
    def test_check_permission_raises_exception(self):
        """Test that check_permission raises exception for unauthorized access."""
        self.rbac.assign_role('user@example.com', Role.USER)
        
        with pytest.raises(HTTPException) as exc_info:
            self.rbac.check_permission('user@example.com', Permission.MANAGE_USERS)
        
        assert exc_info.value.status_code == 403
    
    def test_list_all_users(self):
        """Test listing all users."""
        self.rbac.assign_role('user1@example.com', Role.ADMIN)
        self.rbac.assign_role('user2@example.com', Role.USER)
        
        users = self.rbac.list_all_users()
        
        assert 'user1@example.com' in users
        assert 'user2@example.com' in users
        assert users['user1@example.com'] == 'admin'
        assert users['user2@example.com'] == 'user'
    
    @patch.dict('os.environ', {'ADMIN_EMAILS': 'admin@example.com,super@example.com'})
    def test_admin_from_environment(self):
        """Test admin assignment from environment variable."""
        rbac = RBACManager()
        
        role = rbac.get_user_role('admin@example.com')
        assert role == Role.ADMIN
        
        role = rbac.get_user_role('super@example.com')
        assert role == Role.ADMIN


@pytest.mark.asyncio
class TestAuthDependencies:
    """Test FastAPI auth dependencies."""
    
    @patch('app.auth.oidc.get_oidc_validator')
    async def test_get_current_user_success(self, mock_get_validator):
        """Test successful user authentication."""
        mock_validator = Mock()
        mock_validator.verify_token.return_value = {
            'email': 'test@example.com',
            'sub': '12345',
            'name': 'Test User'
        }
        mock_get_validator.return_value = mock_validator
        
        mock_credentials = Mock()
        mock_credentials.credentials = 'valid-token'
        
        user = await get_current_user(mock_credentials, mock_validator)
        
        assert user['email'] == 'test@example.com'
        assert user['sub'] == '12345'
    
    @patch('app.auth.oidc.get_oidc_validator')
    async def test_get_optional_user_with_no_credentials(self, mock_get_validator):
        """Test optional authentication with no credentials."""
        mock_validator = Mock()
        mock_get_validator.return_value = mock_validator
        
        user = await get_optional_user(None, mock_validator)
        
        assert user is None


@pytest.mark.asyncio
class TestRolePermissionDependencies:
    """Test role and permission dependencies."""
    
    async def test_require_permission_authorized(self):
        """Test permission requirement with authorized user."""
        mock_user = {'email': 'admin@example.com'}
        rbac_manager.assign_role('admin@example.com', Role.ADMIN)
        
        dependency = require_permission(Permission.VIEW_ANALYTICS)
        result = await dependency(mock_user)
        
        assert result is None  # No exception raised
    
    async def test_require_permission_unauthorized(self):
        """Test permission requirement with unauthorized user."""
        mock_user = {'email': 'user@example.com'}
        rbac_manager.assign_role('user@example.com', Role.USER)
        
        dependency = require_permission(Permission.MANAGE_USERS)
        
        with pytest.raises(HTTPException) as exc_info:
            await dependency(mock_user)
        
        assert exc_info.value.status_code == 403
    
    async def test_require_role_authorized(self):
        """Test role requirement with authorized user."""
        mock_user = {'email': 'admin@example.com'}
        rbac_manager.assign_role('admin@example.com', Role.ADMIN)
        
        dependency = require_role(Role.ADMIN)
        result = await dependency(mock_user)
        
        assert result is None
    
    async def test_require_role_unauthorized(self):
        """Test role requirement with unauthorized user."""
        mock_user = {'email': 'user@example.com'}
        rbac_manager.assign_role('user@example.com', Role.USER)
        
        dependency = require_role(Role.ADMIN)
        
        with pytest.raises(HTTPException) as exc_info:
            await dependency(mock_user)
        
        assert exc_info.value.status_code == 403


# Run with: pytest tests/test_auth.py -v --cov=app/auth --cov-report=term
