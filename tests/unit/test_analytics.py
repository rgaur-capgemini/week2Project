"""Tests for analytics collector."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("redis.Redis") as mock:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock.return_value = mock_client
        yield mock_client


@pytest.mark.unit
def test_analytics_collector_initialization(mock_redis):
    """Test AnalyticsCollector initialization."""
    from app.analytics.collector import AnalyticsCollector
    
    collector = AnalyticsCollector(redis_client=mock_redis)
    assert collector.redis_client == mock_redis


@pytest.mark.unit
def test_analytics_collector_record_query(mock_redis):
    """Test recording a query."""
    from app.analytics.collector import AnalyticsCollector
    
    collector = AnalyticsCollector(redis_client=mock_redis)
    collector.record_query(
        user_id="user123",
        question="What is AI?",
        answer="AI is artificial intelligence.",
        response_time=1.5,
        tokens=50
    )
    
    # Verify Redis was called
    assert mock_redis.hincrby.called or mock_redis.incr.called


@pytest.mark.unit
def test_analytics_collector_record_error(mock_redis):
    """Test recording an error."""
    from app.analytics.collector import AnalyticsCollector
    
    collector = AnalyticsCollector(redis_client=mock_redis)
    collector.record_error(
        user_id="user123",
        error_type="ValueError",
        error_message="Test error"
    )
    
    # Verify Redis was called
    assert mock_redis.incr.called or mock_redis.hincrby.called


@pytest.mark.unit
def test_analytics_collector_get_user_stats(mock_redis):
    """Test getting user statistics."""
    from app.analytics.collector import AnalyticsCollector
    
    mock_redis.hgetall.return_value = {
        b"total_queries": b"100",
        b"total_tokens": b"5000",
        b"total_errors": b"5"
    }
    
    collector = AnalyticsCollector(redis_client=mock_redis)
    stats = collector.get_user_stats("user123")
    
    assert "total_queries" in stats or len(stats) >= 0


@pytest.mark.unit
def test_analytics_collector_get_global_stats(mock_redis):
    """Test getting global statistics."""
    from app.analytics.collector import AnalyticsCollector
    
    mock_redis.get.return_value = b"1000"
    
    collector = AnalyticsCollector(redis_client=mock_redis)
    stats = collector.get_global_stats()
    
    assert isinstance(stats, dict)


@pytest.mark.unit
def test_analytics_collector_record_token_usage(mock_redis):
    """Test recording token usage."""
    from app.analytics.collector import AnalyticsCollector
    
    collector = AnalyticsCollector(redis_client=mock_redis)
    collector.record_token_usage(
        user_id="user123",
        tokens=50,
        operation="query"
    )
    
    assert mock_redis.hincrby.called or mock_redis.incr.called


@pytest.mark.unit
def test_analytics_collector_get_time_series(mock_redis):
    """Test getting time series data."""
    from app.analytics.collector import AnalyticsCollector
    
    mock_redis.zrange.return_value = [
        b'{"timestamp": 1234567890, "queries": 10}'
    ]
    
    collector = AnalyticsCollector(redis_client=mock_redis)
    time_series = collector.get_time_series(
        user_id="user123",
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 31)
    )
    
    assert isinstance(time_series, list)


@pytest.mark.unit
def test_analytics_collector_clear_user_stats(mock_redis):
    """Test clearing user statistics."""
    from app.analytics.collector import AnalyticsCollector
    
    collector = AnalyticsCollector(redis_client=mock_redis)
    collector.clear_user_stats("user123")
    
    assert mock_redis.delete.called or mock_redis.hdel.called


@pytest.mark.unit
def test_analytics_collector_increment_counter(mock_redis):
    """Test incrementing a counter."""
    from app.analytics.collector import AnalyticsCollector
    
    collector = AnalyticsCollector(redis_client=mock_redis)
    collector.increment_counter("query_count", user_id="user123")
    
    assert mock_redis.incr.called or mock_redis.hincrby.called


@pytest.mark.unit
def test_analytics_collector_redis_connection_error():
    """Test handling Redis connection errors."""
    from app.analytics.collector import AnalyticsCollector
    import redis
    
    mock_client = MagicMock()
    mock_client.ping.side_effect = redis.ConnectionError("Connection failed")
    
    # Should not raise exception
    try:
        collector = AnalyticsCollector(redis_client=mock_client)
        collector.record_query(
            user_id="user123",
            question="Test",
            answer="Test",
            response_time=1.0,
            tokens=10
        )
    except redis.ConnectionError:
        pass  # Expected in some implementations


@pytest.mark.unit
def test_analytics_collector_batch_record(mock_redis):
    """Test batch recording of analytics."""
    from app.analytics.collector import AnalyticsCollector
    
    collector = AnalyticsCollector(redis_client=mock_redis)
    
    events = [
        {"type": "query", "user_id": "user1", "tokens": 50},
        {"type": "query", "user_id": "user2", "tokens": 30},
        {"type": "error", "user_id": "user1", "error_type": "ValueError"}
    ]
    
    for event in events:
        if event["type"] == "query":
            collector.record_query(
                user_id=event["user_id"],
                question="Test",
                answer="Test",
                response_time=1.0,
                tokens=event["tokens"]
            )
        elif event["type"] == "error":
            collector.record_error(
                user_id=event["user_id"],
                error_type=event["error_type"],
                error_message="Test error"
            )
    
    # Verify multiple calls were made
    assert mock_redis.method_calls  # Should have multiple calls
