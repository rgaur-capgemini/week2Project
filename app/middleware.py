"""
Production-grade middleware: rate limiting, error handling, request validation.
"""

import time
from typing import Callable, Dict
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict, deque
import asyncio
from app.logging_config import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token bucket rate limiting middleware.
    Limits requests per client IP address.
    """
    
    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients: Dict[str, deque] = defaultdict(lambda: deque())
        
        # Cleanup task
        asyncio.create_task(self._cleanup_old_entries())
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Get client IP
        client_ip = request.client.host
        
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/readiness", "/liveness"]:
            return await call_next(request)
        
        # Check rate limit
        now = time.time()
        requests = self.clients[client_ip]
        
        # Remove old requests outside window
        while requests and requests[0] < now - self.window_seconds:
            requests.popleft()
        
        # Check if limit exceeded
        if len(requests) >= self.max_requests:
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                path=request.url.path,
                requests_count=len(requests)
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": self.window_seconds
                }
            )
        
        # Add current request
        requests.append(now)
        
        # Continue processing
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.max_requests - len(requests))
        )
        response.headers["X-RateLimit-Reset"] = str(
            int(now + self.window_seconds)
        )
        
        return response
    
    async def _cleanup_old_entries(self):
        """Periodic cleanup of old rate limit entries."""
        while True:
            await asyncio.sleep(300)  # Cleanup every 5 minutes
            now = time.time()
            
            # Remove entries older than window
            for client_ip in list(self.clients.keys()):
                requests = self.clients[client_ip]
                while requests and requests[0] < now - self.window_seconds:
                    requests.popleft()
                
                # Remove empty entries
                if not requests:
                    del self.clients[client_ip]


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware.
    Catches and logs all unhandled exceptions.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        try:
            response = await call_next(request)
            return response
            
        except HTTPException as e:
            # Re-raise HTTP exceptions (they're handled properly)
            raise
            
        except Exception as e:
            # Log unexpected errors
            logger.error(
                "Unhandled exception",
                error=e,
                method=request.method,
                path=str(request.url.path),
                client_ip=request.client.host
            )
            
            # Return generic error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "An internal error occurred. Please try again later.",
                    "error_id": f"{int(time.time())}"  # For support reference
                }
            )


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Request validation and sanitization middleware.
    """
    
    def __init__(self, app, max_content_length: int = 10 * 1024 * 1024):  # 10MB
        super().__init__(app)
        self.max_content_length = max_content_length
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            if int(content_length) > self.max_content_length:
                logger.warning(
                    "Request too large",
                    content_length=content_length,
                    max_allowed=self.max_content_length
                )
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "detail": f"Request body too large. Maximum allowed: {self.max_content_length} bytes"
                    }
                )
        
        # Continue processing
        response = await call_next(request)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response
