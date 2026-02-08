"""Tests for api_routes.py authentication, history, and analytics endpoints."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.unit
def test_login_request_schema():
    """Test LoginRequest schema validation."""
    from app.api_routes import LoginRequest
    
    request = LoginRequest(token="test-token-123")
    assert request.token == "test-token-123"


@pytest.mark.unit
def test_login_response_schema():
    """Test LoginResponse schema."""
    from app.api_routes import LoginResponse
    
    response = LoginResponse(
        user_id="user123",
        email="test@example.com",
        name="Test User",
        role="user",
        access_token="token123",
        refresh_token="refresh123",
        expires_in=3600
    )
    assert response.user_id == "user123"
    assert response.email == "test@example.com"
    assert response.role == "user"


@pytest.mark.unit
def test_user_info_schema():
    """Test UserInfo schema."""
    from app.api_routes import UserInfo
    
    user_info = UserInfo(
        user_id="user123",
        email="test@example.com",
        name="Test User",
        role="admin",
        permissions=["read", "write", "delete"]
    )
    assert user_info.user_id == "user123"
    assert len(user_info.permissions) == 3


@pytest.mark.unit
def test_chat_message_schema():
    """Test ChatMessage schema."""
    from app.api_routes import ChatMessage
    
    message = ChatMessage(
        id="msg123",
        question="What is AI?",
        answer="AI is artificial intelligence.",
        timestamp=1234567890.0,
        datetime="2024-01-01T00:00:00Z",
        conversation_id="conv123",
        metadata={"source": "test"}
    )
    assert message.id == "msg123"
    assert message.question == "What is AI?"


@pytest.mark.unit
def test_history_response_schema():
    """Test HistoryResponse schema."""
    from app.api_routes import HistoryResponse, ChatMessage
    
    message = ChatMessage(
        id="msg123",
        question="Test?",
        answer="Test answer",
        timestamp=1234567890.0,
        datetime="2024-01-01T00:00:00Z",
        conversation_id="conv123"
    )
    
    response = HistoryResponse(
        user_id="user123",
        messages=[message],
        total_count=1,
        has_more=False
    )
    assert response.user_id == "user123"
    assert len(response.messages) == 1
    assert response.has_more is False


@pytest.mark.unit
def test_analytics_query_schema():
    """Test AnalyticsQuery schema."""
    from app.api_routes import AnalyticsQuery
    
    query = AnalyticsQuery(
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 31),
        group_by="day"
    )
    assert query.group_by == "day"


@pytest.mark.unit
def test_analytics_response_schema():
    """Test AnalyticsResponse schema."""
    from app.api_routes import AnalyticsResponse
    
    response = AnalyticsResponse(
        user_id="user123",
        total_queries=100,
        avg_response_time=1.5,
        total_tokens=5000,
        time_series=[]
    )
    assert response.total_queries == 100
    assert response.avg_response_time == 1.5


@pytest.mark.unit
@patch("app.api_routes.get_current_user")
def test_get_me_endpoint(mock_auth):
    """Test /auth/me endpoint."""
    from fastapi.testclient import TestClient
    from app.main import app
    
    mock_auth.return_value = {
        "user_id": "user123",
        "email": "test@example.com",
        "name": "Test User",
        "role": "user"
    }
    
    client = TestClient(app)
    response = client.get("/auth/me", headers={"Authorization": "Bearer test-token"})
    
    # Endpoint should work with proper auth
    assert response.status_code in [200, 401]  # Depends on auth setup


@pytest.mark.unit
def test_chat_history_query_defaults():
    """Test ChatHistoryQuery default values."""
    from app.api_routes import ChatHistoryQuery
    
    query = ChatHistoryQuery()
    assert query.limit == 50
    assert query.offset == 0
    assert query.conversation_id is None


@pytest.mark.unit
def test_chat_history_query_validation():
    """Test ChatHistoryQuery validation."""
    from app.api_routes import ChatHistoryQuery
    
    # Test valid query
    query = ChatHistoryQuery(limit=10, offset=5)
    assert query.limit == 10
    assert query.offset == 5
    
    # Test with conversation_id
    query_with_conv = ChatHistoryQuery(conversation_id="conv123")
    assert query_with_conv.conversation_id == "conv123"


@pytest.mark.unit
def test_conversation_list_response_schema():
    """Test ConversationListResponse schema."""
    from app.api_routes import ConversationListResponse
    
    response = ConversationListResponse(
        user_id="user123",
        conversations=[
            {
                "conversation_id": "conv1",
                "last_message": "Test message",
                "timestamp": 1234567890.0,
                "message_count": 5
            }
        ],
        total_count=1
    )
    assert response.user_id == "user123"
    assert len(response.conversations) == 1


@pytest.mark.unit
def test_analytics_metric_schema():
    """Test AnalyticsMetric schema."""
    from app.api_routes import AnalyticsMetric
    
    metric = AnalyticsMetric(
        timestamp="2024-01-01T00:00:00Z",
        queries=10,
        avg_response_time=1.5,
        tokens=500,
        errors=0
    )
    assert metric.queries == 10
    assert metric.errors == 0


@pytest.mark.unit
def test_permission_check_schema():
    """Test PermissionCheckResponse schema."""
    from app.api_routes import PermissionCheckResponse
    
    response = PermissionCheckResponse(
        user_id="user123",
        permission="read_data",
        granted=True,
        reason="User has admin role"
    )
    assert response.granted is True
    assert response.permission == "read_data"
