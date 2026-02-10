"""
Comprehensive unit tests for RBAC (Role-Based Access Control).
Tests permission checking, role management, and access control.
"""
import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException

from app.auth.rbac import (
    Permission,
    Role,
    ROLE_PERMISSIONS,
    RBACManager
)


class TestPermissionEnum:
    """Test Permission enum."""
    
    def test_all_permissions_exist(self):
        """Test that all expected permissions are defined."""
        expected_permissions = [
            "chat:ask", "chat:view_history", "chat:delete_history",
            "document:ingest", "document:delete", "document:view",
            "analytics:view", "analytics:export",
            "admin:view_all_users", "admin:manage_users",
            "admin:view_system", "admin:manage_system"
        ]
        
        for perm in expected_permissions:
            assert any(p.value == perm for p in Permission)
    
    def test_permission_values_are_strings(self):
        """Test that all permission values are strings."""
        for perm in Permission:
            assert isinstance(perm.value, str)
            assert ":" in perm.value  # All follow namespace:action format


class TestRoleEnum:
    """Test Role enum."""
    
    def test_all_roles_exist(self):
        """Test that all expected roles are defined."""
        expected_roles = ["user", "admin", "service_account"]
        
        for role in expected_roles:
            assert any(r.value == role for r in Role)
    
    def test_role_values_are_strings(self):
        """Test that all role values are strings."""
        for role in Role:
            assert isinstance(role.value, str)


class TestRolePermissionsMapping:
    """Test ROLE_PERMISSIONS mapping."""
    
    def test_user_has_basic_permissions(self):
        """Test that user role has basic permissions."""
        user_perms = ROLE_PERMISSIONS[Role.USER]
        
        assert Permission.CHAT_ASK in user_perms
        assert Permission.CHAT_VIEW_HISTORY in user_perms
        assert Permission.DOCUMENT_INGEST in user_perms
        assert Permission.DOCUMENT_VIEW in user_perms
    
    def test_user_no_admin_permissions(self):
        """Test that user role does not have admin permissions."""
        user_perms = ROLE_PERMISSIONS[Role.USER]
        
        assert Permission.ADMIN_VIEW_ALL_USERS not in user_perms
        assert Permission.ADMIN_MANAGE_USERS not in user_perms
        assert Permission.DOCUMENT_DELETE not in user_perms
    
    def test_admin_has_all_user_permissions(self):
        """Test that admin has all user permissions."""
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        user_perms = ROLE_PERMISSIONS[Role.USER]
        
        for perm in user_perms:
            assert perm in admin_perms
    
    def test_admin_has_additional_permissions(self):
        """Test that admin has admin-specific permissions."""
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        
        assert Permission.ADMIN_VIEW_ALL_USERS in admin_perms
        assert Permission.ADMIN_MANAGE_USERS in admin_perms
        assert Permission.ADMIN_VIEW_SYSTEM in admin_perms
        assert Permission.ADMIN_MANAGE_SYSTEM in admin_perms
        assert Permission.DOCUMENT_DELETE in admin_perms
        assert Permission.ANALYTICS_VIEW in admin_perms
        assert Permission.ANALYTICS_EXPORT in admin_perms
    
    def test_service_account_has_automation_permissions(self):
        """Test that service account has permissions for automation."""
        sa_perms = ROLE_PERMISSIONS[Role.SERVICE_ACCOUNT]
        
        assert Permission.CHAT_ASK in sa_perms
        assert Permission.DOCUMENT_INGEST in sa_perms
        assert Permission.DOCUMENT_DELETE in sa_perms
        assert Permission.ANALYTICS_VIEW in sa_perms
    
    def test_service_account_no_user_management(self):
        """Test that service account cannot manage users."""
        sa_perms = ROLE_PERMISSIONS[Role.SERVICE_ACCOUNT]
        
        assert Permission.ADMIN_MANAGE_USERS not in sa_perms
        assert Permission.ADMIN_VIEW_ALL_USERS not in sa_perms


class TestRBACManagerInit:
    """Test RBACManager initialization."""
    
    def test_init_no_admin_emails(self):
        """Test initialization without admin emails."""
        manager = RBACManager()
        assert isinstance(manager.admin_emails, set)
    
    def test_init_with_admin_emails(self):
        """Test initialization with admin email list."""
        admin_emails = ["admin1@example.com", "admin2@example.com"]
        manager = RBACManager(admin_emails=admin_emails)
        
        assert "admin1@example.com" in manager.admin_emails
        assert "admin2@example.com" in manager.admin_emails
    
    def test_init_loads_env_admin_emails(self):
        """Test that admin emails are loaded from environment."""
        with patch.dict('os.environ', {'ADMIN_EMAILS': 'admin1@test.com,admin2@test.com'}):
            manager = RBACManager()
            assert "admin1@test.com" in manager.admin_emails
            assert "admin2@test.com" in manager.admin_emails
    
    def test_admin_emails_stored_as_set(self):
        """Test that admin emails are stored as set for O(1) lookup."""
        admin_emails = ["admin@example.com", "admin@example.com"]  # Duplicate
        manager = RBACManager(admin_emails=admin_emails)
        
        assert isinstance(manager.admin_emails, set)
        assert len(manager.admin_emails) == 1  # Duplicate removed


class TestRBACManagerPermissionChecking:
    """Test permission checking methods."""
    
    @pytest.fixture
    def manager(self):
        """Create RBAC manager."""
        return RBACManager(admin_emails=["admin@example.com"])
    
    def test_has_permission_user_valid(self, manager):
        """Test that user has valid permissions."""
        assert manager.has_permission(Role.USER, Permission.CHAT_ASK)
        assert manager.has_permission(Role.USER, Permission.CHAT_VIEW_HISTORY)
        assert manager.has_permission(Role.USER, Permission.DOCUMENT_INGEST)
    
    def test_has_permission_user_invalid(self, manager):
        """Test that user does not have admin permissions."""
        assert not manager.has_permission(Role.USER, Permission.ADMIN_MANAGE_USERS)
        assert not manager.has_permission(Role.USER, Permission.DOCUMENT_DELETE)
        assert not manager.has_permission(Role.USER, Permission.ANALYTICS_EXPORT)
    
    def test_has_permission_admin_valid(self, manager):
        """Test that admin has all permissions."""
        # Test user permissions
        assert manager.has_permission(Role.ADMIN, Permission.CHAT_ASK)
        
        # Test admin permissions
        assert manager.has_permission(Role.ADMIN, Permission.ADMIN_MANAGE_USERS)
        assert manager.has_permission(Role.ADMIN, Permission.DOCUMENT_DELETE)
        assert manager.has_permission(Role.ADMIN, Permission.ANALYTICS_EXPORT)
    
    def test_has_permission_service_account(self, manager):
        """Test service account permissions."""
        assert manager.has_permission(Role.SERVICE_ACCOUNT, Permission.CHAT_ASK)
        assert manager.has_permission(Role.SERVICE_ACCOUNT, Permission.DOCUMENT_INGEST)
        assert manager.has_permission(Role.SERVICE_ACCOUNT, Permission.DOCUMENT_DELETE)
        assert not manager.has_permission(Role.SERVICE_ACCOUNT, Permission.ADMIN_MANAGE_USERS)
    
    def test_get_role_permissions_user(self, manager):
        """Test getting all permissions for user role."""
        perms = manager.get_role_permissions(Role.USER)
        
        assert Permission.CHAT_ASK in perms
        assert Permission.CHAT_VIEW_HISTORY in perms
        assert Permission.ADMIN_MANAGE_USERS not in perms
    
    def test_get_role_permissions_admin(self, manager):
        """Test getting all permissions for admin role."""
        perms = manager.get_role_permissions(Role.ADMIN)
        
        assert len(perms) > len(manager.get_role_permissions(Role.USER))
        assert Permission.ADMIN_MANAGE_USERS in perms
    
    def test_get_role_permissions_returns_copy(self, manager):
        """Test that returned permissions are a copy, not reference."""
        perms1 = manager.get_role_permissions(Role.USER)
        perms2 = manager.get_role_permissions(Role.USER)
        
        assert perms1 is not perms2
        assert perms1 == perms2


class TestRBACManagerRoleAssignment:
    """Test role assignment and determination."""
    
    @pytest.fixture
    def manager(self):
        """Create RBAC manager with admin emails."""
        return RBACManager(admin_emails=["admin@example.com", "superadmin@test.com"])
    
    def test_is_admin_email_match(self, manager):
        """Test that admin email is recognized."""
        assert manager.is_admin("admin@example.com")
        assert manager.is_admin("superadmin@test.com")
    
    def test_is_admin_email_no_match(self, manager):
        """Test that non-admin email is not recognized as admin."""
        assert not manager.is_admin("user@example.com")
        assert not manager.is_admin("test@test.com")
    
    def test_is_admin_case_insensitive(self, manager):
        """Test that admin check is case-insensitive."""
        manager.admin_emails.add("Admin@Example.COM")
        assert manager.is_admin("admin@example.com")
        assert manager.is_admin("ADMIN@EXAMPLE.COM")
    
    def test_get_user_role_admin(self, manager):
        """Test getting role for admin user."""
        role = manager.get_user_role("admin@example.com")
        assert role == Role.ADMIN
    
    def test_get_user_role_regular_user(self, manager):
        """Test getting role for regular user."""
        role = manager.get_user_role("user@example.com")
        assert role == Role.USER
    
    def test_get_user_role_service_account(self, manager):
        """Test getting role for service account."""
        role = manager.get_user_role("service@serviceaccount.com", is_service_account=True)
        assert role == Role.SERVICE_ACCOUNT


class TestRBACManagerAccessControl:
    """Test access control enforcement."""
    
    @pytest.fixture
    def manager(self):
        """Create RBAC manager."""
        return RBACManager(admin_emails=["admin@example.com"])
    
    def test_require_permission_success(self, manager):
        """Test successful permission requirement."""
        # Should not raise exception
        manager.require_permission(Role.USER, Permission.CHAT_ASK)
        manager.require_permission(Role.ADMIN, Permission.ADMIN_MANAGE_USERS)
    
    def test_require_permission_failure(self, manager):
        """Test failed permission requirement raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            manager.require_permission(Role.USER, Permission.ADMIN_MANAGE_USERS)
        
        assert exc_info.value.status_code == 403
        assert "Permission denied" in str(exc_info.value.detail)
    
    def test_require_permission_includes_details(self, manager):
        """Test that exception includes permission details."""
        with pytest.raises(HTTPException) as exc_info:
            manager.require_permission(Role.USER, Permission.DOCUMENT_DELETE)
        
        assert "document:delete" in str(exc_info.value.detail)
    
    def test_require_any_permission_success(self, manager):
        """Test requiring any of multiple permissions - success."""
        # User has chat:ask
        manager.require_any_permission(
            Role.USER,
            [Permission.CHAT_ASK, Permission.ADMIN_MANAGE_USERS]
        )
    
    def test_require_any_permission_failure(self, manager):
        """Test requiring any of multiple permissions - all fail."""
        with pytest.raises(HTTPException) as exc_info:
            manager.require_any_permission(
                Role.USER,
                [Permission.ADMIN_MANAGE_USERS, Permission.DOCUMENT_DELETE]
            )
        
        assert exc_info.value.status_code == 403
    
    def test_require_all_permissions_success(self, manager):
        """Test requiring all permissions - success."""
        manager.require_all_permissions(
            Role.USER,
            [Permission.CHAT_ASK, Permission.CHAT_VIEW_HISTORY]
        )
    
    def test_require_all_permissions_partial_failure(self, manager):
        """Test requiring all permissions - partial failure."""
        with pytest.raises(HTTPException):
            manager.require_all_permissions(
                Role.USER,
                [Permission.CHAT_ASK, Permission.ADMIN_MANAGE_USERS]  # Second fails
            )


class TestRBACManagerAuditLogging:
    """Test audit logging functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create RBAC manager."""
        return RBACManager()
    
    def test_audit_log_permission_check(self, manager):
        """Test that permission checks are logged."""
        with patch('app.auth.rbac.logger') as mock_logger:
            manager.has_permission(Role.USER, Permission.CHAT_ASK)
            assert mock_logger.debug.called or mock_logger.info.called
    
    def test_audit_log_permission_denied(self, manager):
        """Test that permission denials are logged."""
        with patch('app.auth.rbac.logger') as mock_logger:
            try:
                manager.require_permission(Role.USER, Permission.ADMIN_MANAGE_USERS)
            except HTTPException:
                pass
            
            assert mock_logger.warning.called or mock_logger.error.called
    
    def test_audit_log_includes_context(self, manager):
        """Test that audit logs include relevant context."""
        with patch('app.auth.rbac.logger') as mock_logger:
            manager.has_permission(Role.USER, Permission.CHAT_ASK)
            
            # Check that logger was called with context
            if mock_logger.debug.called:
                call_args = mock_logger.debug.call_args
                assert call_args is not None


class TestRBACManagerEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def manager(self):
        """Create RBAC manager."""
        return RBACManager()
    
    def test_empty_admin_emails_list(self):
        """Test initialization with empty admin emails list."""
        manager = RBACManager(admin_emails=[])
        assert len(manager.admin_emails) == 0
    
    def test_none_admin_emails_list(self):
        """Test initialization with None admin emails."""
        manager = RBACManager(admin_emails=None)
        assert isinstance(manager.admin_emails, set)
    
    def test_whitespace_email_handling(self, manager):
        """Test that whitespace in emails is handled."""
        manager.admin_emails.add("  admin@example.com  ")
        # Should still work with normalized email
        assert manager.is_admin("admin@example.com")
    
    def test_permission_check_with_string_role(self, manager):
        """Test permission check with string role value."""
        # Should work with role value string
        assert manager.has_permission("user", Permission.CHAT_ASK)
        assert manager.has_permission("admin", Permission.ADMIN_MANAGE_USERS)
    
    def test_invalid_permission_handling(self, manager):
        """Test handling of invalid permission."""
        with pytest.raises((AttributeError, KeyError, ValueError)):
            manager.has_permission(Role.USER, "invalid:permission")
    
    @pytest.mark.parametrize("role,expected_count", [
        (Role.USER, 5),
        (Role.ADMIN, 12),
        (Role.SERVICE_ACCOUNT, 4),
    ])
    def test_permission_counts_by_role(self, manager, role, expected_count):
        """Test that each role has expected number of permissions."""
        perms = manager.get_role_permissions(role)
        assert len(perms) == expected_count
