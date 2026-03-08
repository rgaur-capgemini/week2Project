"""
Feature Flags Manager - Week 4
Manages feature flags for A/B testing and canary releases.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from app.logging_config import get_logger

logger = get_logger(__name__)


class FeatureFlagStatus(str, Enum):
    """Feature flag status."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    TESTING = "testing"


class FeatureFlagManager:
    """
    Manages feature flags for gradual feature rollouts and A/B testing.
    """
    
    def __init__(self, firestore_client):
        """
        Initialize feature flag manager.
        
        Args:
            firestore_client: Firestore client instance
        """
        self.db = firestore_client
        self.flags_collection = "feature_flags"
    
    def create_flag(
        self,
        flag_name: str,
        description: str,
        status: FeatureFlagStatus = FeatureFlagStatus.DISABLED,
        rollout_percentage: float = 0.0,
        enabled_users: Optional[List[str]] = None,
        enabled_groups: Optional[List[str]] = None
    ) -> str:
        """
        Create a new feature flag.
        
        Args:
            flag_name: Unique flag name
            description: Flag description
            status: Initial status
            rollout_percentage: Percentage of users to enable (0-100)
            enabled_users: List of specific user IDs to enable
            enabled_groups: List of user groups to enable
            
        Returns:
            Flag ID
        """
        try:
            flag_doc = {
                "flag_id": flag_name,
                "description": description,
                "status": status.value,
                "rollout_percentage": rollout_percentage,
                "enabled_users": enabled_users or [],
                "enabled_groups": enabled_groups or [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "usage_count": 0
            }
            
            self.db.collection(self.flags_collection).document(flag_name).set(flag_doc)
            
            logger.info(f"Created feature flag: {flag_name}")
            return flag_name
            
        except Exception as e:
            logger.error(f"Error creating feature flag: {e}")
            raise
    
    def is_enabled(
        self,
        flag_name: str,
        user_id: Optional[str] = None,
        user_groups: Optional[List[str]] = None
    ) -> bool:
        """
        Check if a feature flag is enabled for a user.
        
        Args:
            flag_name: Flag name
            user_id: User ID to check
            user_groups: User's groups
            
        Returns:
            True if enabled, False otherwise
        """
        try:
            # Get flag
            doc = self.db.collection(self.flags_collection).document(flag_name).get()
            if not doc.exists:
                logger.warning(f"Flag {flag_name} not found, defaulting to disabled")
                return False
            
            flag = doc.to_dict()
            status = flag.get("status")
            
            # If globally disabled, return False
            if status == FeatureFlagStatus.DISABLED.value:
                return False
            
            # If globally enabled, return True
            if status == FeatureFlagStatus.ENABLED.value:
                return True
            
            # If testing, check specific conditions
            if status == FeatureFlagStatus.TESTING.value:
                # Check if user is specifically enabled
                if user_id and user_id in flag.get("enabled_users", []):
                    return True
                
                # Check if user's group is enabled
                if user_groups:
                    enabled_groups = set(flag.get("enabled_groups", []))
                    if any(group in enabled_groups for group in user_groups):
                        return True
                
                # Check rollout percentage (using hash for consistency)
                rollout_percentage = flag.get("rollout_percentage", 0.0)
                if user_id and rollout_percentage > 0:
                    import hashlib
                    hash_value = int(hashlib.md5(f"{flag_name}:{user_id}".encode()).hexdigest(), 16)
                    percentage = (hash_value % 10000) / 100.0
                    if percentage < rollout_percentage:
                        return True
                
                return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking feature flag: {e}")
            return False
    
    def enable_flag(self, flag_name: str) -> bool:
        """
        Enable a feature flag globally.
        
        Args:
            flag_name: Flag name
            
        Returns:
            Success status
        """
        try:
            self.db.collection(self.flags_collection).document(flag_name).update({
                "status": FeatureFlagStatus.ENABLED.value,
                "updated_at": datetime.utcnow()
            })
            
            logger.info(f"Enabled feature flag: {flag_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error enabling feature flag: {e}")
            return False
    
    def disable_flag(self, flag_name: str) -> bool:
        """
        Disable a feature flag globally.
        
        Args:
            flag_name: Flag name
            
        Returns:
            Success status
        """
        try:
            self.db.collection(self.flags_collection).document(flag_name).update({
                "status": FeatureFlagStatus.DISABLED.value,
                "updated_at": datetime.utcnow()
            })
            
            logger.info(f"Disabled feature flag: {flag_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error disabling feature flag: {e}")
            return False
    
    def update_rollout_percentage(self, flag_name: str, percentage: float) -> bool:
        """
        Update rollout percentage for gradual rollout.
        
        Args:
            flag_name: Flag name
            percentage: New rollout percentage (0-100)
            
        Returns:
            Success status
        """
        try:
            if not 0 <= percentage <= 100:
                raise ValueError("Percentage must be between 0 and 100")
            
            self.db.collection(self.flags_collection).document(flag_name).update({
                "rollout_percentage": percentage,
                "status": FeatureFlagStatus.TESTING.value if percentage < 100 else FeatureFlagStatus.ENABLED.value,
                "updated_at": datetime.utcnow()
            })
            
            logger.info(f"Updated rollout percentage for {flag_name} to {percentage}%")
            return True
            
        except Exception as e:
            logger.error(f"Error updating rollout percentage: {e}")
            return False
    
    def add_enabled_user(self, flag_name: str, user_id: str) -> bool:
        """
        Add a user to the enabled list.
        
        Args:
            flag_name: Flag name
            user_id: User ID to enable
            
        Returns:
            Success status
        """
        try:
            doc = self.db.collection(self.flags_collection).document(flag_name).get()
            if not doc.exists:
                return False
            
            flag = doc.to_dict()
            enabled_users = flag.get("enabled_users", [])
            
            if user_id not in enabled_users:
                enabled_users.append(user_id)
                self.db.collection(self.flags_collection).document(flag_name).update({
                    "enabled_users": enabled_users,
                    "updated_at": datetime.utcnow()
                })
                
                logger.info(f"Added user {user_id} to flag {flag_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding enabled user: {e}")
            return False
    
    def remove_enabled_user(self, flag_name: str, user_id: str) -> bool:
        """
        Remove a user from the enabled list.
        
        Args:
            flag_name: Flag name
            user_id: User ID to remove
            
        Returns:
            Success status
        """
        try:
            doc = self.db.collection(self.flags_collection).document(flag_name).get()
            if not doc.exists:
                return False
            
            flag = doc.to_dict()
            enabled_users = flag.get("enabled_users", [])
            
            if user_id in enabled_users:
                enabled_users.remove(user_id)
                self.db.collection(self.flags_collection).document(flag_name).update({
                    "enabled_users": enabled_users,
                    "updated_at": datetime.utcnow()
                })
                
                logger.info(f"Removed user {user_id} from flag {flag_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing enabled user: {e}")
            return False
    
    def list_flags(self, status: Optional[FeatureFlagStatus] = None) -> List[Dict[str, Any]]:
        """
        List all feature flags.
        
        Args:
            status: Filter by status
            
        Returns:
            List of feature flags
        """
        try:
            query = self.db.collection(self.flags_collection)
            
            if status:
                query = query.where("status", "==", status.value)
            
            flags = []
            for doc in query.stream():
                flag_data = doc.to_dict()
                flag_data["flag_id"] = doc.id
                flags.append(flag_data)
            
            logger.info(f"Listed {len(flags)} feature flags")
            return flags
            
        except Exception as e:
            logger.error(f"Error listing feature flags: {e}")
            return []
    
    def get_flag(self, flag_name: str) -> Optional[Dict[str, Any]]:
        """
        Get feature flag details.
        
        Args:
            flag_name: Flag name
            
        Returns:
            Flag data or None
        """
        try:
            doc = self.db.collection(self.flags_collection).document(flag_name).get()
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"Error getting feature flag: {e}")
            return None


# Predefined feature flags for Week 4
WEEK4_FEATURE_FLAGS = {
    "gemini_flash_model": {
        "description": "Use Gemini Flash model instead of Pro",
        "status": FeatureFlagStatus.TESTING,
        "rollout_percentage": 20.0
    },
    "advanced_embeddings": {
        "description": "Use multilingual embeddings",
        "status": FeatureFlagStatus.TESTING,
        "rollout_percentage": 10.0
    },
    "cost_optimization": {
        "description": "Enable aggressive cost optimization features",
        "status": FeatureFlagStatus.ENABLED,
        "rollout_percentage": 100.0
    },
    "detailed_observability": {
        "description": "Enable detailed observability traces",
        "status": FeatureFlagStatus.ENABLED,
        "rollout_percentage": 100.0
    }
}


# _week4
