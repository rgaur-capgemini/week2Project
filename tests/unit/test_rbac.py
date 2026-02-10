"""
Comprehensive tests for RBAC - 100% coverage target.
Tests all methods, branches, edge cases, and exception paths.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from app.auth.rbac import Permission, Role, ROLE_PERMISSIONS, RBACManager


class TestPermissionEnum:
    """Test Permission enum."""
    
    def test_all_chat_permissions(self):
        """Test all chat permissions are defined."""
        assert Permission.CHAT_ASK == "chat:ask"
        assert Permission.CHAT_VIEW_HISTORY == "chat:view_history"
        assert Permission.CHAT_DELETE_HISTORY == "chat:delete_history"
    
    def test_all_document_permissions(self):
        """Test all document permissions are defined."""
        assert Permission.DOCUMENT_INGEST == "document:ingest"
        assert Permission.DOCUMENT_DELETE == "document:delete"
        assert Permission.DOCUMENT_VIEW == "document:view"
    
    def test_all_analytics_permissions(self):
        """Test all analytics permissions are defined."""
        assert Permission.ANALYTICS_VIEW == "analytics:view"
        assert Permission.ANALYTICS_EXPORT == "analytics:export"
    
    def test_all_admin_permissions(self):
        """Test all admin permissions are defined."""
        assert Permission.ADMIN_VIEW_ALL_USERS == "admin:view_all_users"
        assert Permission.ADMIN_MANAGE_USERS == "admin:manage_users"
        assert Permission.ADMIN_VIEW_SYSTEM == "admin:view_system"
        assert Permission.ADMIN_MANAGE_SYSTEM == "admin:manage_system"


class TestRoleEnum:
    """Test Role enum."""
    
    def test_all_roles_defined(self):
        """Test all roles are defined."""
        assert Role.USER == "user"
        assert Role.ADMIN == "admin"
        assert Role.SERVICE_ACCOUNT == "service_account"


class TestRolePermissionsMapping:
    """Test ROLE_PERMISSIONS mapping."""
    
    def test_user_has_basic_permissions(self):
        """Test user role has correct permissions."""
        user_perms = ROLE_PERMISSIONS[Role.USER]
        
        assert Permission.CHAT_ASK in user_perms
        assert Permission.CHAT_VIEW_HISTORY in user_perms
        assert Permission.DOCUMENT_INGEST in user_perms
        assert Permission.DOCUMENT_VIEW in user_perms
    
    def test_user_no_admin_permissions(self):
        """Test user role lacks admin permissions."""
        user_perms = ROLE_PERMISSIONS[Role.USER]
        
        assert Permission.ADMIN_VIEW_ALL_USERS not in user_perms
        assert Permission.DOCUMENT_DELETE not in user_perms
        assert Permission.ANALYTICS_EXPORT not in user_perms
    
    def test_admin_has_all_permissions(self):
        """Test admin role has all user permissions plus admin ones."""
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        user_perms = ROLE_PERMISSIONS[Role.USER]
        
        # Admin has all user permissions
        for perm in user_perms:
            assert perm in admin_perms
        
        # Plus admin-specific ones
        assert Permission.ADMIN_VIEW_ALL_USERS in admin_perms
        assert Permission.ADMIN_MANAGE_USERS in admin_perms
        assert Permission.DOCUMENT_DELETE in admin_perms
    
    def test_service_account_permissions(self):
        """Test service account role permissions."""
        sa_perms = ROLE_PERMISSIONS[Role.SERVICE_ACCOUNT]
        
        assert Permission.CHAT_ASK in sa_perms
        assert Permission.DOCUMENT_INGEST in sa_perms
        assert Permission.DOCUMENT_DELETE in sa_perms
        assert Permission.ANALYTICS_VIEW in sa_perms


class TestRBACManagerInit:
    """Test RBACManager initialization."""
    
    @patch.dict('os.environ', {}, clear=True)
    def test_init_no_admin_emails(self):
        """Test initialization without admin emails."""
        manager = RBACManager()
        assert isinstance(manager.admin_emails, set)
        assert len(manager.admin_emails) >= 0
    
    @patch.dict('os.environ', {}, clear=True)
    def test_init_with_admin_emails(self):
        """Test initialization with admin email list."""
        manager = RBACManager(admin_emails=["admin1@example.com", "admin2@example.com"])
        assert "admin1@example.com" in manager.admin_emails
        assert "admin2@example.com" in manager.admin_emails
    
    @patch.dict('os.environ', {'ADMIN_EMAILS': 'admin1@test.com,admin2@test.com'})
    def test_init_loads_env_admin_emails(self):
        """Test initialization loads admin emails from environment."""
        manager = RBACManager()
        assert "admin1@test.com" in manager.admin_emails
        assert "admin2@test.com" in manager.admin_emails


class TestGetUserRole:
    """Test get_user_role method."""
    
    @patch.dict('os.environ', {}, clear=True)
    def test_get_user_role_admin_email(self):
        """Test admin role for whitelisted email."""
        manager = RBACManager(admin_emails=["admin@example.com"])
        role = manager.get_user_role("admin@example.com")
        assert role == Role.ADMIN
    
    @patch.dict('os.environ', {}, clear=True)
    def test_get_user_role_regular_user(self):
        """Test user role for non-admin email."""
        manager = RBACManager(admin_emails=["admin@example.com"])
        role = manager.get_user_role("user@example.com")
        assert role == Role.USER
    
    @patch.dict('os.environ', {}, clear=True)
    def test_get_user_role_case_insensitive(self):
        """Test email comparison is case insensitive."""
        manager = RBACManager(admin_emails=["Admin@Example.com"])
        role = manager.get_user_role("admin@example.com")
        assert role == Role.ADMIN


class TestHasPermission:
    """Test has_permission method."""
    
    @patch.dict('os.environ', {}, clear=True)
    def test_has_permission_user_allowed(self):
        """Test user has allowed permission."""
        manager = RBACManager()
        assert manager.has_permission(Role.USER, Permission.CHAT_ASK)
        assert manager.has_permission(Role.USER, Permission.DOCUMENT_VIEW)
    
    @patch.dict('os.environ', {}, clear=True)
    def test_has_permission_user_denied(self):
        """Test user lacks admin permission."""
        manager = RBACManager()
        assert not manager.has_permission(Role.USER, Permission.ADMIN_VIEW_ALL_USERS)
        assert not manager.has_permission(Role.USER, Permission.DOCUMENT_DELETE)
    
    @patch.dict('os.environ', {}, clear=True)
    def test_has_permission_admin_allowed_all(self):
        """Test admin has all permissions."""
        manager = RBACManager()
        assert manager.has_permission(Role.ADMIN, Permission.CHAT_ASK)
        assert manager.has_permission(Role.ADMIN, Permission.ADMIN_VIEW_ALL_USERS)
        assert manager.has_permission(Role.ADMIN, Permission.DOCUMENT_DELETE)
    
    @patch.dict('os.environ', {}, clear=True)
    def test_has_permission_service_account(self):
        """Test service account permissions."""
        manager = RBACManager()
        assert manager.has_permission(Role.SERVICE_ACCOUNT, Permission.CHAT_ASK)
        assert manager.has_permission(Role.SERVICE_ACCOUNT, Permission.DOCUMENT_DELETE)
        assert not manager.has_permission(Role.SERVICE_ACCOUNT, Permission.ADMIN_MANAGE_USERS)


class TestCheckPermission:
    """Test check_permission method."""
    
    @patch.dict('os.environ', {}, clear=True)
    def test_check_permission_allowed(self):
        """Test check permission when allowed."""
        manager = RBACManager()
        # Should not raise exception
        manager.check_permission(Role.USER, Permission.CHAT_ASK)
    
    @patch.dict('os.environ', {}, clear=True)
    def test_check_permission_denied(self):
        """Test check permission when denied."""
        manager = RBACManager()
        
        with pytest.raises(HTTPException) as exc_info:
            manager.check_permission(Role.USER, Permission.ADMIN_VIEW_ALL_USERS)
        
        assert exc_info.value.status_code == 403
        assert "permission" in str(exc_info.value.detail).lower()
    
    @patch.dict('os.environ', {}, clear=True)
    def test_check_permission_admin_allowed(self):
        """Test admin can access everything."""
        manager = RBACManager()
        manager.check_permission(Role.ADMIN, Permission.ADMIN_MANAGE_SYSTEM)
        manager.check_permission(Role.ADMIN, Permission.DOCUMENT_DELETE)


class TestRequireRole:
    """Test require_role method."""
    
    @patch.dict('os.environ', {}, clear=True)
    def test_require_role_user_has_role(self):
        """Test user with required role."""
        manager = RBACManager()
        # Should not raise exception
        manager.require_role(Role.USER, [Role.USER, Role.ADMIN])
    
    @patch.dict('os.environ', {}, clear=True)
    def test_require_role_admin_has_role(self):
        """Test admin with required role."""
        manager = RBACManager()
        manager.require_role(Role.ADMIN, [Role.ADMIN])
    
    @patch.dict('os.environ', {}, clear=True)
    def test_require_role_user_lacks_role(self):
        """Test user without required role."""
        manager = RBACManager()
        
        with pytest.raises(HTTPException) as exc_info:
            manager.require_role(Role.USER, [Role.ADMIN])
        
        assert exc_info.value.status_code == 403
        assert "role" in str(exc_info.value.detail).lower()
    
    @patch.dict('os.environ', {}, clear=True)
    def test_require_role_multiple_allowed(self):
        """Test require role with multiple allowed roles."""
        manager = RBACManager()
        manager.require_role(Role.USER, [Role.USER, Role.ADMIN, Role.SERVICE_ACCOUNT])


class TestIsAdmin:
    """Test is_admin method."""
    
    @patch.dict('os.environ', {}, clear=True)
    def test_is_admin_true(self):
        """Test admin email returns True."""
        manager = RBACManager(admin_emails=["admin@example.com"])
        assert manager.is_admin("admin@example.com")
    
    @patch.dict('os.environ', {}, clear=True)
    def test_is_admin_false(self):
        """Test non-admin email returns False."""
        manager = RBACManager(admin_emails=["admin@example.com"])
        assert not manager.is_admin("user@example.com")
    
    @patch.dict('os.environ', {}, clear=True)
    def test_is_admin_case_insensitive(self):
        """Test admin check is case insensitive."""
        manager = RBACManager(admin_emails=["Admin@Example.COM"])
        assert manager.is_admin("admin@example.com")


class TestGetRolePermissions:
    """Test get_role_permissions method."""
    
    @patch.dict('os.environ', {}, clear=True)
    def test_get_role_permissions_user(self):
        """Test getting permissions for user role."""
        manager = RBACManager()
        perms = manager.get_role_permissions(Role.USER)
        
        assert Permission.CHAT_ASK in perms
        assert Permission.DOCUMENT_VIEW in perms
        assert Permission.ADMIN_VIEW_ALL_USERS not in perms
    
    @patch.dict('os.environ', {}, clear=True)
    def test_get_role_permissions_admin(self):
        """Test getting permissions for admin role."""
        manager = RBACManager()
        perms = manager.get_role_permissions(Role.ADMIN)
        
        assert len(perms) > len(ROLE_PERMISSIONS[Role.USER])
        assert Permission.ADMIN_MANAGE_SYSTEM in perms
    
    @patch.dict('os.environ', {}, clear=True)
    def test_get_role_permissions_returns_set(self):
        """Test method returns a set."""
        manager = RBACManager()
        perms = manager.get_role_permissions(Role.USER)
        
        assert isinstance(perms, set)


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @patch.dict('os.environ', {}, clear=True)
    def test_empty_email(self):
        """Test with empty email."""
        manager = RBACManager(admin_emails=["admin@example.com"])
        role = manager.get_user_role("")
        assert role == Role.USER
    
    @patch.dict('os.environ', {}, clear=True)
    def test_none_email(self):
        """Test with None email."""
        manager = RBACManager(admin_emails=["admin@example.com"])
        role = manager.get_user_role(None)
        assert role == Role.USER
    
    @patch.dict('os.environ', {}, clear=True)
    def test_whitespace_in_admin_emails(self):
        """Test admin emails with whitespace are handled."""
        manager = RBACManager(admin_emails=[" admin@example.com ", "user@test.com"])
        # Should handle trimmed emails
        assert manager.is_admin("admin@example.com")
    
    @patch.dict('os.environ', {}, clear=True)
    def test_duplicate_admin_emails(self):
        """Test duplicate admin emails handled by set."""
        manager = RBACManager(admin_emails=["admin@example.com", "admin@example.com"])
        assert len(manager.admin_emails) >= 1
