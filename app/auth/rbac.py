"""
Role-Based Access Control (RBAC) Implementation
Defines roles, permissions, and authorization logic
"""

from enum import Enum
from typing import List, Set, Dict, Any
from fastapi import HTTPException, Depends
from app.auth.oidc import get_current_user
from app.logging_config import get_logger

logger = get_logger(__name__)


class Role(str, Enum):
    """User roles in the system."""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class Permission(str, Enum):
    """Granular permissions."""
    # Document operations
    UPLOAD_DOCUMENT = "upload:document"
    DELETE_DOCUMENT = "delete:document"
    VIEW_DOCUMENT = "view:document"
    
    # Query operations
    QUERY_RAG = "query:rag"
    VIEW_HISTORY = "view:history"
    DELETE_HISTORY = "delete:history"
    
    # Admin operations
    VIEW_ANALYTICS = "view:analytics"
    MANAGE_USERS = "manage:users"
    VIEW_LOGS = "view:logs"
    CONFIGURE_SYSTEM = "configure:system"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        # All permissions
        Permission.UPLOAD_DOCUMENT,
        Permission.DELETE_DOCUMENT,
        Permission.VIEW_DOCUMENT,
        Permission.QUERY_RAG,
        Permission.VIEW_HISTORY,
        Permission.DELETE_HISTORY,
        Permission.VIEW_ANALYTICS,
        Permission.MANAGE_USERS,
        Permission.VIEW_LOGS,
        Permission.CONFIGURE_SYSTEM,
    },
    Role.USER: {
        Permission.UPLOAD_DOCUMENT,
        Permission.VIEW_DOCUMENT,
        Permission.QUERY_RAG,
        Permission.VIEW_HISTORY,
        Permission.DELETE_HISTORY,
    },
    Role.VIEWER: {
        Permission.VIEW_DOCUMENT,
        Permission.QUERY_RAG,
        Permission.VIEW_HISTORY,
    }
}


class RBACManager:
    """Manages role assignments and permission checks."""
    
    def __init__(self):
        # In production, this would be stored in Firestore or database
        # For now, using in-memory storage with default admin
        self._user_roles: Dict[str, Role] = {
            # Default admin users (can be configured via env)
        }
        
    def assign_role(self, user_email: str, role: Role):
        """Assign a role to a user."""
        self._user_roles[user_email] = role
        logger.info("Role assigned", user_email=user_email, role=role.value)
    
    def get_user_role(self, user_email: str) -> Role:
        """Get user's role. Defaults to USER if not assigned."""
        # Check if user is admin (from environment or config)
        import os
        admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
        admin_emails = [email.strip().lower() for email in admin_emails if email.strip()]
        
        if user_email.lower() in admin_emails:
            return Role.ADMIN
        
        return self._user_roles.get(user_email, Role.USER)
    
    def get_user_permissions(self, user_email: str) -> Set[Permission]:
        """Get all permissions for a user based on their role."""
        role = self.get_user_role(user_email)
        return ROLE_PERMISSIONS.get(role, set())
    
    def has_permission(self, user_email: str, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        permissions = self.get_user_permissions(user_email)
        return permission in permissions
    
    def check_permission(self, user_email: str, permission: Permission):
        """Check permission and raise exception if not authorized."""
        if not self.has_permission(user_email, permission):
            logger.warning(
                "Permission denied",
                user_email=user_email,
                permission=permission.value
            )
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission.value}"
            )
    
    def list_all_users(self) -> Dict[str, str]:
        """List all users and their roles (admin only)."""
        return {email: role.value for email, role in self._user_roles.items()}


# Global RBAC manager instance
rbac_manager = RBACManager()


def require_permission(permission: Permission):
    """
    Decorator/dependency to require a specific permission.
    
    Usage:
        @app.post("/documents")
        async def upload_doc(
            user: dict = Depends(get_current_user),
            _auth: None = Depends(require_permission(Permission.UPLOAD_DOCUMENT))
        ):
            # User has permission, proceed
            pass
    """
    async def permission_checker(user: Dict[str, Any] = Depends(get_current_user)):
        rbac_manager.check_permission(user['email'], permission)
        return None
    
    return permission_checker


def require_role(required_role: Role):
    """
    Decorator/dependency to require a specific role.
    
    Usage:
        @app.get("/admin/users")
        async def list_users(
            user: dict = Depends(get_current_user),
            _auth: None = Depends(require_role(Role.ADMIN))
        ):
            pass
    """
    async def role_checker(user: Dict[str, Any] = Depends(get_current_user)):
        user_role = rbac_manager.get_user_role(user['email'])
        
        # Check role hierarchy: admin > user > viewer
        role_hierarchy = {Role.ADMIN: 3, Role.USER: 2, Role.VIEWER: 1}
        
        if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 999):
            logger.warning(
                "Role requirement not met",
                user_email=user['email'],
                user_role=user_role.value,
                required_role=required_role.value
            )
            raise HTTPException(
                status_code=403,
                detail=f"Role '{required_role.value}' required"
            )
        
        return None
    
    return role_checker


async def get_current_user_with_role(
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Enhanced user dependency that includes role and permissions.
    """
    user_email = user['email']
    user['role'] = rbac_manager.get_user_role(user_email).value
    user['permissions'] = [p.value for p in rbac_manager.get_user_permissions(user_email)]
    return user
