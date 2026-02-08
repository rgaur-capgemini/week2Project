"""
JWT Token Handler for custom token generation and refresh.
"""

import os
import time
import jwt
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from app.logging_config import get_logger
from app.config import config

logger = get_logger(__name__)


class JWTHandler:
    """
    Custom JWT token handler for API-to-API communication.
    
    Security features:
    - HS256 algorithm for signing
    - Configurable expiration
    - Refresh token support
    - Automatic secret rotation support
    """
    
    def __init__(self):
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        self.refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    def _get_secret(self) -> str:
        """Get JWT secret from Secret Manager."""
        try:
            secret = config.get_secret("chatbot-jwt-secret")
            if not secret:
                raise RuntimeError("JWT secret not configured")
            return secret
        except Exception as e:
            logger.error(f"Could not retrieve JWT secret: {e}")
            # Fallback for local development
            return os.getenv("JWT_SECRET_KEY", "development-secret-change-in-production")
    
    def create_access_token(
        self,
        user_id: str,
        email: str,
        role: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new access token.
        
        Args:
            user_id: User identifier
            email: User email
            role: User role (user, admin)
            additional_claims: Additional claims to include
        
        Returns:
            Encoded JWT token
        """
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "user_id": user_id,
            "email": email,
            "role": role,
            "token_type": "access",
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "nbf": int(now.timestamp()),  # Not before
        }
        
        # Add additional claims
        if additional_claims:
            payload.update(additional_claims)
        
        secret = self._get_secret()
        token = jwt.encode(payload, secret, algorithm=self.algorithm)
        
        logger.info(
            "Access token created",
            user_id=user_id,
            role=role,
            expires_at=expire.isoformat()
        )
        
        return token
    
    def create_refresh_token(self, user_id: str, email: str) -> str:
        """
        Create a new refresh token.
        
        Args:
            user_id: User identifier
            email: User email
        
        Returns:
            Encoded refresh token
        """
        now = datetime.utcnow()
        expire = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "user_id": user_id,
            "email": email,
            "token_type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "nbf": int(now.timestamp())
        }
        
        secret = self._get_secret()
        token = jwt.encode(payload, secret, algorithm=self.algorithm)
        
        logger.info(
            "Refresh token created",
            user_id=user_id,
            expires_at=expire.isoformat()
        )
        
        return token
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: JWT token to decode
        
        Returns:
            Decoded payload
        
        Raises:
            jwt.ExpiredSignatureError: If token is expired
            jwt.InvalidTokenError: If token is invalid
        """
        secret = self._get_secret()
        
        payload = jwt.decode(
            token,
            secret,
            algorithms=[self.algorithm],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_nbf": True
            }
        )
        
        return payload
    
    def verify_token(self, token: str) -> bool:
        """
        Verify if token is valid.
        
        Args:
            token: JWT token to verify
        
        Returns:
            True if valid, False otherwise
        """
        try:
            self.decode_token(token)
            return True
        except jwt.ExpiredSignatureError:
            logger.debug("Token expired")
            return False
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid token: {e}")
            return False
    
    def refresh_access_token(self, refresh_token: str, role: str) -> str:
        """
        Generate a new access token from a refresh token.
        
        Args:
            refresh_token: Valid refresh token
            role: User role
        
        Returns:
            New access token
        
        Raises:
            jwt.InvalidTokenError: If refresh token is invalid
        """
        payload = self.decode_token(refresh_token)
        
        # Verify it's a refresh token
        if payload.get("token_type") != "refresh":
            raise jwt.InvalidTokenError("Not a refresh token")
        
        # Create new access token
        return self.create_access_token(
            user_id=payload["user_id"],
            email=payload["email"],
            role=role
        )
    
    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """
        Get token expiration time.
        
        Args:
            token: JWT token
        
        Returns:
            Expiration datetime or None if invalid
        """
        try:
            payload = self.decode_token(token)
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp)
            return None
        except jwt.InvalidTokenError:
            return None
