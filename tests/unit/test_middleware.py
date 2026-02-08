"""Tests for middleware.py."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import time
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.middleware import (
    RateLimitMiddleware,
    ErrorHandlingMiddleware,
    RequestValidationMiddleware,
    SecurityHeadersMiddleware
)


@pytest.fixture
def test_app():
    """Create a test FastAPI app."""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "success"}
    
    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    return app


@pytest.mark.unit
def test_rate_limit_middleware_init():
    """Test RateLimitMiddleware initialization."""
    app = FastAPI()
    middleware = RateLimitMiddleware(app, max_requests=100, window_seconds=60)
    
    assert middleware.max_requests == 100
    assert middleware.window_seconds == 60
    assert len(middleware.clients) == 0


@pytest.mark.unit
def test_rate_limit_middleware_allows_requests(test_app):
    """Test rate limit middleware allows normal requests."""
    test_app.add_middleware(RateLimitMiddleware, max_requests=10, window_seconds=60)
    client = TestClient(test_app)
    
    response = client.get("/test")
    assert response.status_code == 200


@pytest.mark.unit
def test_rate_limit_middleware_blocks_excessive_requests(test_app):
    """Test rate limit middleware blocks excessive requests."""
    test_app.add_middleware(RateLimitMiddleware, max_requests=3, window_seconds=60)
    client = TestClient(test_app)
    
    # Make 3 requests (should succeed)
    for _ in range(3):
        response = client.get("/test")
        assert response.status_code == 200
    
    # 4th request should be rate limited
    response = client.get("/test")
    assert response.status_code == 429


@pytest.mark.unit
def test_rate_limit_middleware_skips_health_check(test_app):
    """Test rate limit middleware skips health check endpoints."""
    test_app.add_middleware(RateLimitMiddleware, max_requests=1, window_seconds=60)
    client = TestClient(test_app)
    
    # Health checks should not be rate limited
    for _ in range(5):
        response = client.get("/health")
        assert response.status_code == 200


@pytest.mark.unit
def test_error_handling_middleware_catches_exceptions(test_app):
    """Test error handling middleware catches exceptions."""
    test_app.add_middleware(ErrorHandlingMiddleware)
    client = TestClient(test_app)
    
    response = client.get("/error")
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data


@pytest.mark.unit
def test_error_handling_middleware_logs_errors(test_app):
    """Test error handling middleware logs errors."""
    test_app.add_middleware(ErrorHandlingMiddleware)
    client = TestClient(test_app)
    
    with patch("app.middleware.logger") as mock_logger:
        response = client.get("/error")
        assert mock_logger.error.called


@pytest.mark.unit
def test_security_headers_middleware_adds_headers(test_app):
    """Test security headers middleware adds security headers."""
    test_app.add_middleware(SecurityHeadersMiddleware)
    client = TestClient(test_app)
    
    response = client.get("/test")
    
    # Check security headers are present
    assert "x-content-type-options" in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "x-frame-options" in response.headers
    assert "x-xss-protection" in response.headers


@pytest.mark.unit
def test_request_validation_middleware_validates_content_type(test_app):
    """Test request validation middleware validates content type."""
    test_app.add_middleware(RequestValidationMiddleware)
    
    @test_app.post("/data")
    async def post_data(data: dict):
        return data
    
    client = TestClient(test_app)
    
    # Valid JSON request
    response = client.post(
        "/data",
        json={"key": "value"},
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200


@pytest.mark.unit
def test_request_validation_middleware_checks_request_size(test_app):
    """Test request validation middleware checks request size."""
    test_app.add_middleware(RequestValidationMiddleware, max_request_size=100)
    
    @test_app.post("/data")
    async def post_data(data: dict):
        return data
    
    client = TestClient(test_app)
    
    # Small request should succeed
    response = client.post("/data", json={"key": "value"})
    assert response.status_code == 200


@pytest.mark.unit
def test_middleware_chain_order(test_app):
    """Test middleware chain executes in correct order."""
    # Add multiple middlewares
    test_app.add_middleware(SecurityHeadersMiddleware)
    test_app.add_middleware(ErrorHandlingMiddleware)
    test_app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
    
    client = TestClient(test_app)
    response = client.get("/test")
    
    assert response.status_code == 200
    # Security headers should be present
    assert "x-content-type-options" in response.headers


@pytest.mark.unit
def test_rate_limit_window_expiration():
    """Test rate limit window properly expires old requests."""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "success"}
    
    # Short window for testing
    app.add_middleware(RateLimitMiddleware, max_requests=2, window_seconds=1)
    client = TestClient(app)
    
    # Make 2 requests
    client.get("/test")
    client.get("/test")
    
    # Wait for window to expire
    time.sleep(1.1)
    
    # Should be able to make requests again
    response = client.get("/test")
    assert response.status_code == 200


@pytest.mark.unit
def test_error_handling_preserves_http_exceptions(test_app):
    """Test error handling middleware preserves HTTPException."""
    from fastapi import HTTPException
    
    @test_app.get("/http-error")
    async def http_error():
        raise HTTPException(status_code=404, detail="Not found")
    
    test_app.add_middleware(ErrorHandlingMiddleware)
    client = TestClient(test_app)
    
    response = client.get("/http-error")
    assert response.status_code == 404
    assert "not found" in response.text.lower()
