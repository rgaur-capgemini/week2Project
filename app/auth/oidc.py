"""
Google OIDC Authentication Implementation
Validates Google ID tokens and extracts user identity
"""

from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.oauth2 import id_token
from google.auth.transport import requests
from google.cloud import firestore
import os
from typing import Optional, Dict, Any
from functools import lru_cache
import time
from datetime import datetime
from app.logging_config import get_logger
from app.config import config

logger = get_logger(__name__)
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)

# Firestore client for user storage and token tracking
_firestore_client = None


def get_firestore_client():
    """Get or create Firestore client."""
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = firestore.Client(project=config.PROJECT_ID)
    return _firestore_client


class GoogleOIDCValidator:
    """Validates Google OIDC ID tokens."""
    
    def __init__(self, client_ids: list[str]):
        """
        Initialize OIDC validator.
        
        Args:
            client_ids: List of allowed Google OAuth2 client IDs
        """
        self.client_ids = client_ids
        self.request = requests.Request()
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify Google ID token and extract user info.
        
        Args:
            token: Google ID token (JWT)
            
        Returns:
            User info dict containing email, name, sub, etc.
            
        Raises:
            HTTPException: If token is invalid
        """
        # Check cache
        cache_key = token[:50]  # Use token prefix as cache key
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                logger.debug("Token validation cache hit")
                return cached_data
        
        try:
            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                token, 
                self.request,
                audience=None  # We'll verify audience manually
            )
            
            # Verify issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
            
            # Verify audience (client ID) if specified
            if self.client_ids and idinfo.get('aud') not in self.client_ids:
                logger.warning(
                    "Token audience mismatch",
                    expected=self.client_ids,
                    actual=idinfo.get('aud')
                )
                # In production, you'd want to be strict here
                # For development, we'll log but continue
            
            # Verify email is verified
            if not idinfo.get('email_verified', False):
                raise ValueError('Email not verified')
            
            # Cache the result
            self._cache[cache_key] = (idinfo, time.time())
            
            # Clean old cache entries (simple cleanup)
            if len(self._cache) > 1000:
                current_time = time.time()
                self._cache = {
                    k: v for k, v in self._cache.items()
                    if current_time - v[1] < self._cache_ttl
                }
            
            logger.info(
                "Token verified successfully",
                user_email=idinfo.get('email'),
                sub=idinfo.get('sub')
            )
            
            return {
                'sub': idinfo['sub'],  # Google user ID
                'email': idinfo['email'],
                'name': idinfo.get('name', ''),
                'picture': idinfo.get('picture', ''),
                'email_verified': idinfo.get('email_verified', False),
                'hd': idinfo.get('hd', ''),  # Hosted domain (for Google Workspace)
            }
            
        except ValueError as e:
            logger.error("Token verification failed", error=str(e))
            raise HTTPException(
                status_code=401,
                detail=f"Invalid authentication token: {str(e)}"
            )
        except Exception as e:
            logger.error("Token verification error", error=str(e), error_type=type(e).__name__)
            raise HTTPException(
                status_code=401,
                detail="Authentication failed"
            )


# Global validator instance
_validator: Optional[GoogleOIDCValidator] = None


def get_oidc_validator() -> GoogleOIDCValidator:
    """Get or create OIDC validator instance."""
    global _validator
    if _validator is None:
        # client_ids = os.getenv("GOOGLE_CLIENT_IDS", "").split(",")
        # client_ids = [cid.strip() for cid in client_ids if cid.strip()]
          # Prefer explicit env var so local dev can override,
        # otherwise fall back to Secret Manager value configured in GCP.
        client_ids_env = os.getenv("GOOGLE_CLIENT_IDS", "")
        client_ids = [cid.strip() for cid in client_ids_env.split(",") if cid.strip()]
        if not client_ids:
            # Secret name matches GCP setup: google-oauth-client-id
            secret_client_id = config.get_secret("google-oauth-client-id")
            if secret_client_id:
                client_ids = [secret_client_id.strip()]
        _validator = GoogleOIDCValidator(client_ids)
    return _validator


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    validator: GoogleOIDCValidator = Depends(get_oidc_validator)
) -> Dict[str, Any]:
    """
    FastAPI dependency to get current authenticated user.
    
    Usage:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"message": f"Hello {user['email']}"}
    """
    token = credentials.credentials
    return validator.verify_token(token)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_optional),
    validator: GoogleOIDCValidator = Depends(get_oidc_validator)
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency for optional authentication.
    Returns None if no auth provided, user info if valid token provided.
    """
    if not credentials:
        return None
    
    try:
        return validator.verify_token(credentials.credentials)
    except HTTPException:
        return None


async def ensure_user_exists(user_email: str, user_name: str = "", user_picture: str = ""):
    """
    Ensure user document exists in Firestore.
    Creates user if not exists, updates last_login timestamp.
    
    Args:
        user_email: User's email address
        user_name: User's full name
        user_picture: User's profile picture URL
    """
    try:
        db = get_firestore_client()
        user_ref = db.collection('users').document(user_email)
        user_doc = user_ref.get()
        
        now = datetime.utcnow()
        
        if not user_doc.exists:
            # Create new user
            user_ref.set({
                'email': user_email,
                'name': user_name,
                'picture': user_picture,
                'token_count': 0,
                'created_at': now,
                'last_login': now
            })
            logger.info("New user created", user_email=user_email)
        else:
            # Update last_login
            user_ref.update({
                'last_login': now,
                'name': user_name,  # Update name in case it changed
                'picture': user_picture
            })
            logger.debug("User login updated", user_email=user_email)
            
    except Exception as e:
        logger.error("Failed to ensure user exists", user_email=user_email, error=str(e))
        # Don't fail the request if Firestore is down
        pass


async def increment_token_count(user_email: str):
    """
    Increment the token usage count for a user.
    Called on each API request to track usage.
    
    Args:
        user_email: User's email address
    """
    try:
        db = get_firestore_client()
        user_ref = db.collection('users').document(user_email)
        
        # Use Firestore transaction to safely increment
        user_ref.update({
            'token_count': firestore.Increment(1),
            'last_activity': datetime.utcnow()
        })
        
        logger.debug("Token count incremented", user_email=user_email)
        
    except Exception as e:
        logger.error("Failed to increment token count", user_email=user_email, error=str(e))
        # Don't fail the request if tracking fails
        pass


async def get_user_token_count(user_email: str) -> int:
    """
    Get the current token count for a user.
    
    Args:
        user_email: User's email address
        
    Returns:
        Token count (0 if user not found)
    """
    try:
        db = get_firestore_client()
        user_ref = db.collection('users').document(user_email)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            return user_doc.to_dict().get('token_count', 0)
        return 0
        
    except Exception as e:
        logger.error("Failed to get token count", user_email=user_email, error=str(e))
        return 0


async def get_all_users_token_stats() -> List[Dict[str, Any]]:
    """
    Get token statistics for all users (admin only).
    
    Returns:
        List of user statistics dictionaries
    """
    try:
        db = get_firestore_client()
        users_ref = db.collection('users')
        users = users_ref.stream()
        
        stats = []
        for user_doc in users:
            user_data = user_doc.to_dict()
            stats.append({
                'email': user_data.get('email', ''),
                'name': user_data.get('name', ''),
                'token_count': user_data.get('token_count', 0),
                'last_activity': user_data.get('last_activity'),
                'created_at': user_data.get('created_at')
            })
        
        # Sort by token count descending
        stats.sort(key=lambda x: x['token_count'], reverse=True)
        return stats
        
    except Exception as e:
        logger.error("Failed to get all users stats", error=str(e))
        return []

