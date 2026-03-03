"""
A/B testing middleware for canary releases and experiments.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
import random
import hashlib
from app.logging_config import get_logger

logger = get_logger(__name__)


class ABTestingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to assign users to A/B test cohorts.
    
    Strategies:
    - Random: Random assignment
    - Sticky: Consistent assignment based on user_id
    - Percentage: Gradual rollout (10%, 25%, 50%, etc.)
    """
    
    def __init__(
        self,
        app,
        canary_percentage: int = 10,
        strategy: str = "sticky"
    ):
        super().__init__(app)
        self.canary_percentage = canary_percentage
        self.strategy = strategy
    
    async def dispatch(self, request: Request, call_next):
        """Assign user to cohort and route accordingly."""
        
        # Extract user identifier
        user_id = self._get_user_id(request)
        
        # Determine cohort
        is_canary = self._assign_cohort(user_id)
        
        # Add cohort to request state
        request.state.is_canary = is_canary
        request.state.cohort = "canary" if is_canary else "stable"
        
        # Log assignment
        logger.debug(
            "A/B test assignment",
            extra={"user_id": user_id, "cohort": request.state.cohort}
        )
        
        response = await call_next(request)
        
        # Add cohort info to response headers
        response.headers["X-Cohort"] = request.state.cohort
        
        return response
    
    def _get_user_id(self, request: Request) -> str:
        """Extract user ID from request."""
        # Try to get from auth token
        if hasattr(request.state, "user"):
            user = request.state.user
            if isinstance(user, dict):
                return user.get("user_id", "anonymous")
            elif hasattr(user, "user_id"):
                return user.user_id
        
        # Fallback to session ID or IP
        session_id = request.cookies.get("session_id")
        if session_id:
            return session_id
        
        return request.client.host if request.client else "anonymous"
    
    def _assign_cohort(self, user_id: str) -> bool:
        """
        Assign user to canary cohort.
        
        Returns:
            True if user is in canary, False otherwise
        """
        if self.strategy == "random":
            return random.randint(0, 100) < self.canary_percentage
        
        elif self.strategy == "sticky":
            # Consistent hashing for sticky assignment
            hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
            return (hash_value % 100) < self.canary_percentage
        
        else:
            return False
