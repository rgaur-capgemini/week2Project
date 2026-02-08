"""
Role-Based Access Control (RBAC) implementation.
Enforces permissions based on user roles.
"""

from enum import Enum
from typing import Dict, Set, List, Any, Optional
from fastapi import HTTPException, status

from app.logging_config import get_logger

logger = get_logger(__name__)


class Permission(str, Enum):
    """System permissions."""
    
    # Chat permissions
    CHAT_ASK = "chat:ask"
    CHAT_VIEW_HISTORY = "chat:view_history"
    CHAT_DELETE_HISTORY = "chat:delete_history"
    
    # Document permissions
    DOCUMENT_INGEST = "document:ingest"
    DOCUMENT_DELETE = "document:delete"
    DOCUMENT_VIEW = "document:view"
    
    # Analytics permissions
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_EXPORT = "analytics:export"
    
    # Admin permissions
    ADMIN_VIEW_ALL_USERS = "admin:view_all_users"
    ADMIN_MANAGE_USERS = "admin:manage_users"
    ADMIN_VIEW_SYSTEM = "admin:view_system"
    ADMIN_MANAGE_SYSTEM = "admin:manage_system"


class Role(str, Enum):
    """User roles."""
    USER = "user"
    ADMIN = "admin"
    SERVICE_ACCOUNT = "service_account"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.USER: {
        Permission.CHAT_ASK,
        Permission.CHAT_VIEW_HISTORY,
        Permission.CHAT_DELETE_HISTORY,
        Permission.DOCUMENT_INGEST,
        Permission.DOCUMENT_VIEW,
    },
    Role.ADMIN: {
        # Admin has all user permissions plus admin-specific ones
        Permission.CHAT_ASK,
        Permission.CHAT_VIEW_HISTORY,
        Permission.CHAT_DELETE_HISTORY,
        Permission.DOCUMENT_INGEST,
        Permission.DOCUMENT_DELETE,
        Permission.DOCUMENT_VIEW,
        Permission.ANALYTICS_VIEW,
        Permission.ANALYTICS_EXPORT,
        Permission.ADMIN_VIEW_ALL_USERS,
        Permission.ADMIN_MANAGE_USERS,
        Permission.ADMIN_VIEW_SYSTEM,
        Permission.ADMIN_MANAGE_SYSTEM,
    },
    Role.SERVICE_ACCOUNT: {
        # Service accounts can do everything for automated tasks
        Permission.CHAT_ASK,
        Permission.DOCUMENT_INGEST,
        Permission.DOCUMENT_DELETE,
        Permission.ANALYTICS_VIEW,
    }
}


class RBACManager:
    """
    Role-Based Access Control manager.
    
    Features:
    - Role-based permission checking
    - Admin email whitelist
    - Audit logging
    """
    
    def __init__(self, admin_emails: Optional[List[str]] = None):
        """
        Initialize RBAC manager.
        
        Args:
            admin_emails: List of admin email addresses
        """
        self.admin_emails = set(admin_emails or [])
        
        # Add default admin emails from environment
        import os
        default_admins = os.getenv("ADMIN_EMAILS", "").split(",")
        self.admin_emails.update(email.strip() for email in default_admins if email.strip())
        
        logger.info(
            "RBAC Manager initialized",
            num_admin_emails=len(self.admin_emails)
        )
    
    def get_user_role(self, user_info: Dict[str, Any]) -> Role:
        """
        Determine user role from user information.
        
        Args:
            user_info: User information dictionary
        
        Returns:
            User role
        """
        email = user_info.get("email", "")
        
        # Check if user is in admin whitelist
        if email in self.admin_emails:
            logger.info(f"User {email} identified as ADMIN")
            return Role.ADMIN
        
        # Check if service account
        if user_info.get("is_service_account", False):
            return Role.SERVICE_ACCOUNT
        
        # Default role
        return Role.USER
    
    def get_permissions(self, role: Role) -> Set[Permission]:
        """
        Get all permissions for a role.
        
        Args:
            role: User role
        
        Returns:
            Set of permissions
        """
        return ROLE_PERMISSIONS.get(role, set())
    
    def has_permission(self, user_info: Dict[str, Any], permission: Permission) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            user_info: User information
            permission: Permission to check
        
        Returns:
            True if user has permission
        """
        role = self.get_user_role(user_info)
        permissions = self.get_permissions(role)
        has_perm = permission in permissions
        
        if not has_perm:
            logger.warning(
                "Permission denied",
                user=user_info.get("email"),
                role=role,
                permission=permission
            )
        
        return has_perm
    
    def require_permission(
        self,
        user_info: Dict[str, Any],
        permission: Permission
    ):
        """
        Require a specific permission - raises exception if not authorized.
        
        Args:
            user_info: User information
            permission: Required permission
        
        Raises:
            HTTPException: If user lacks permission
        """
        if not self.has_permission(user_info, permission):
            role = self.get_user_role(user_info)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value} required (current role: {role.value})"
            )
    
    def require_role(self, user_info: Dict[str, Any], required_role: Role):
        """
        Require a specific role - raises exception if not authorized.
        
        Args:
            user_info: User information
            required_role: Required role
        
        Raises:
            HTTPException: If user doesn't have required role
        """
        actual_role = self.get_user_role(user_info)
        
        # Admin can access everything
        if actual_role == Role.ADMIN:
            return
        
        if actual_role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {required_role.value} required (current: {actual_role.value})"
            )
    
    def add_admin_email(self, email: str):
        """Add an email to admin whitelist."""
        self.admin_emails.add(email)
        logger.info(f"Added admin email: {email}")
    
    def remove_admin_email(self, email: str):
        """Remove an email from admin whitelist."""
        self.admin_emails.discard(email)
        logger.info(f"Removed admin email: {email}")
    
    def is_admin(self, user_info: Dict[str, Any]) -> bool:
        """Check if user is admin."""
        return self.get_user_role(user_info) == Role.ADMIN


# Global RBAC manager instance
_rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """Get global RBAC manager (singleton)."""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager


def require_permission(permission: Permission):
    """
    Decorator factory for requiring specific permissions.
    
    Usage:
        @app.get("/admin/stats")
        @require_permission(Permission.ANALYTICS_VIEW)
        async def get_stats(user: dict = Depends(get_current_user)):
            return {"stats": "data"}
    """
    def decorator(func):
        async def wrapper(*args, user: Optional[Dict[str, Any]] = None, **kwargs):
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            rbac = get_rbac_manager()
            rbac.require_permission(user, permission)
            
            return await func(*args, user=user, **kwargs)
        
        return wrapper
    return decorator


def require_role(required_role: Role):
    """
    Decorator factory for requiring specific roles.
    
    Usage:
        @app.get("/admin/users")
        @require_role(Role.ADMIN)
        async def get_users(user: dict = Depends(get_current_user)):
            return {"users": [...]}
    """
    def decorator(func):
        async def wrapper(*args, user: Optional[Dict[str, Any]] = None, **kwargs):
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            rbac = get_rbac_manager()
            rbac.require_role(user, required_role)
            
            return await func(*args, user=user, **kwargs)
        
        return wrapper
    return decorator
