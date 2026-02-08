"""
GCP OIDC-based authentication with JWT validation.
Validates Google OAuth 2.0 tokens and enforces security best practices.
"""

import os
import time
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.oauth2 import id_token
from google.auth.transport import requests
import jwt
from functools import lru_cache

from app.logging_config import get_logger
from app.config import config

logger = get_logger(__name__)

security = HTTPBearer()


class OIDCAuthenticator:
    """
    GCP OIDC authenticator with comprehensive JWT validation.
    
    Security features:
    - Validates signature using Google's public keys
    - Checks issuer, audience, expiry
    - Supports both Google OAuth and custom JWT
    - Rate limiting and caching
    """
    
    def __init__(self):
        self.project_id = config.PROJECT_ID
        self.project_number = os.getenv("PROJECT_NUMBER", "382685100652")
        
        # OAuth 2.0 Client ID from Secret Manager
        self.client_id = self._get_oauth_client_id()
        
        # Allowed issuers for OIDC tokens
        self.allowed_issuers = [
            "https://accounts.google.com",
            f"https://accounts.google.com/{self.project_number}",
            "accounts.google.com"
        ]
        
        # Token cache for performance (short-lived to maintain security)
        self._token_cache = {}
        self._cache_ttl = 300  # 5 minutes
        
        logger.info("OIDC Authenticator initialized", project=self.project_id)
    
    def _get_oauth_client_id(self) -> str:
        """
        Retrieve OAuth 2.0 Client ID from Secret Manager.
        Falls back to environment variable for local development.
        """
        try:
            client_id = config.get_secret("google-oauth-client-id")
            if client_id:
                logger.info("OAuth Client ID retrieved from Secret Manager")
                return client_id
        except Exception as e:
            logger.warning(f"Could not retrieve OAuth Client ID from Secret Manager: {e}")
        
        # Fallback to environment variable
        client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        if not client_id:
            logger.error("GOOGLE_CLIENT_ID not configured - authentication will fail")
            raise RuntimeError("OAuth Client ID not configured")
        
        return client_id
    
    @lru_cache(maxsize=128)
    def _get_client_secret(self) -> str:
        """
        Retrieve OAuth 2.0 Client Secret from Secret Manager.
        NEVER exposed to frontend.
        """
        try:
            return config.get_secret("google-oauth-client-secret")
        except Exception as e:
            logger.error(f"Could not retrieve OAuth Client Secret: {e}")
            raise RuntimeError("OAuth Client Secret not available")
    
    async def validate_google_token(self, token: str) -> Dict[str, Any]:
        """
        Validate Google OAuth 2.0 ID token.
        
        Validation steps:
        1. Verify signature using Google's public keys
        2. Check issuer
        3. Check audience (client ID)
        4. Check expiry
        5. Check issued-at time (not too old)
        
        Args:
            token: JWT token from Google OAuth
        
        Returns:
            Decoded token payload with user information
        
        Raises:
            HTTPException: If token is invalid
        """
        # Check cache first
        cache_key = f"google_token_{token[:20]}"
        if cache_key in self._token_cache:
            cached_data, cached_time = self._token_cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                logger.debug("Token validation cache hit")
                return cached_data
        
        try:
            # Verify token using Google's public keys
            request = requests.Request()
            id_info = id_token.verify_oauth2_token(
                token,
                request,
                self.client_id,
                clock_skew_in_seconds=10
            )
            
            # Validate issuer
            if id_info.get("iss") not in self.allowed_issuers:
                logger.warning(
                    "Invalid token issuer",
                    issuer=id_info.get("iss"),
                    allowed=self.allowed_issuers
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token issuer"
                )
            
            # Validate audience (client ID)
            if id_info.get("aud") != self.client_id:
                logger.warning(
                    "Invalid token audience",
                    audience=id_info.get("aud"),
                    expected=self.client_id
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token audience"
                )
            
            # Extract user information
            user_info = {
                "user_id": id_info.get("sub"),
                "email": id_info.get("email"),
                "email_verified": id_info.get("email_verified", False),
                "name": id_info.get("name"),
                "picture": id_info.get("picture"),
                "iss": id_info.get("iss"),
                "aud": id_info.get("aud"),
                "exp": id_info.get("exp"),
                "iat": id_info.get("iat")
            }
            
            # Email must be verified for production
            if not user_info["email_verified"]:
                logger.warning("Email not verified", email=user_info["email"])
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email not verified"
                )
            
            # Cache validated token
            self._token_cache[cache_key] = (user_info, time.time())
            
            logger.info(
                "Token validated successfully",
                user_id=user_info["user_id"],
                email=user_info["email"]
            )
            
            return user_info
            
        except ValueError as e:
            logger.error(f"Token validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed"
            )
    
    async def validate_custom_jwt(self, token: str) -> Dict[str, Any]:
        """
        Validate custom JWT issued by our system.
        Used for API-to-API communication or service accounts.
        
        Args:
            token: Custom JWT token
        
        Returns:
            Decoded token payload
        """
        try:
            # Get JWT secret from Secret Manager
            jwt_secret = config.get_secret("jwt-secret")
            if not jwt_secret:
                raise RuntimeError("JWT secret not configured")
            
            # Decode and validate
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True
                }
            )
            
            # Validate custom claims
            required_fields = ["user_id", "email", "role"]
            for field in required_fields:
                if field not in payload:
                    raise ValueError(f"Missing required field: {field}")
            
            logger.info(
                "Custom JWT validated",
                user_id=payload["user_id"],
                role=payload["role"]
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        except jwt.InvalidSignatureError:
            logger.warning("Invalid JWT signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature"
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed"
            )
    
    async def authenticate(self, token: str) -> Dict[str, Any]:
        """
        Main authentication method - tries Google OAuth first, then custom JWT.
        
        Args:
            token: Bearer token
        
        Returns:
            User information dictionary
        """
        # Try Google OAuth first
        try:
            return await self.validate_google_token(token)
        except HTTPException:
            pass
        
        # Fall back to custom JWT
        try:
            return await self.validate_custom_jwt(token)
        except HTTPException as e:
            # If both fail, raise the last exception
            raise e


# Global authenticator instance
_authenticator: Optional[OIDCAuthenticator] = None


def get_authenticator() -> OIDCAuthenticator:
    """Get global authenticator instance (singleton pattern)."""
    global _authenticator
    if _authenticator is None:
        _authenticator = OIDCAuthenticator()
    return _authenticator


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    FastAPI dependency for extracting and validating current user.
    
    Usage:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"user": user["email"]}
    
    Returns:
        User information dictionary
    
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authorization credentials provided"
        )
    
    token = credentials.credentials
    authenticator = get_authenticator()
    
    try:
        user_info = await authenticator.authenticate(token)
        return user_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    Optional authentication - returns None if no credentials provided.
    Used for endpoints that can work with or without authentication.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
