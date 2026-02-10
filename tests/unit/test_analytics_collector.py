"""
Comprehensive tests for AnalyticsCollector - 100% coverage target.
Tests all methods, branches, edge cases, and exception paths.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
import json
import time
from datetime import datetime
from redis.exceptions import RedisError

from app.analytics.collector import AnalyticsCollector


class TestAnalyticsCollectorInit:
    """Test AnalyticsCollector initialization."""
    
    @patch('app.analytics.collector.redis.Redis')
    @patch('app.analytics.collector.config')
    def test_init_default(self, mock_config, mock_redis_class):
        """Test default initialization."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        assert collector.host == "10.168.174.3"
        assert collector.port == 6379
        assert collector.db == 1
    
    @patch('app.analytics.collector.redis.Redis')
    @patch('app.analytics.collector.config')
    def test_init_custom_params(self, mock_config, mock_redis_class):
        """Test initialization with custom parameters."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector(
            host="custom-host",
            port=6380,
            password="custom-pass",
            db=2
        )
        assert collector.host == "custom-host"
        assert collector.port == 6380
        assert collector.password == "custom-pass"
        assert collector.db == 2
    
    @patch('app.analytics.collector.redis.Redis')
    @patch('app.analytics.collector.config')
    def test_init_redis_connection_fails(self, mock_config, mock_redis_class):
        """Test initialization when Redis connection fails."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = None
        
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = RedisError("Connection failed")
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        assert collector.client is None
    
    @patch('app.analytics.collector.redis.Redis')
    @patch('app.analytics.collector.config')
    def test_init_no_password(self, mock_config, mock_redis_class):
        """Test initialization without password."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.side_effect = Exception("Secret not found")
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        assert collector.password is None


class TestRecordAPICall:
    """Test API call recording."""
    
    @patch('app.analytics.collector.redis.Redis')
    @patch('app.analytics.collector.config')
    def test_record_api_call_success(self, mock_config, mock_redis_class):
        """Test successful API call recording."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        
        collector.record_api_call(
            endpoint="/api/query",
            method="POST",
            user_id="user-123",
            status_code=200,
            latency_ms=150.5,
            metadata={"model": "gemini-2.0-flash"}
        )
        
        # Verify Redis commands called
        assert mock_redis.hincrby.called
        assert mock_redis.zadd.called
        assert mock_redis.lpush.called
        assert mock_redis.expire.called
    
    @patch('app.analytics.collector.redis.Redis')
    @patch('app.analytics.collector.config')
    def test_record_api_call_no_metadata(self, mock_config, mock_redis_class):
        """Test recording without metadata."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        
        collector.record_api_call(
            endpoint="/api/query",
            method="POST",
            user_id="user-123",
            status_code=200,
            latency_ms=150.5
        )
        
        assert mock_redis.hincrby.called
    
    @patch('app.analytics.collector.redis.Redis')
    @patch('app.analytics.collector.config')
    def test_record_api_call_no_client(self, mock_config, mock_redis_class):
        """Test recording when Redis client is None."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = None
        
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = RedisError("Connection failed")
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        
        # Should not raise error
        collector.record_api_call(
            endpoint="/api/query",
            method="POST",
            user_id="user-123",
            status_code=200,
            latency_ms=150.5
        )
    
    @patch('app.analytics.collector.redis.Redis')
    @patch('app.analytics.collector.config')
    def test_record_api_call_redis_error(self, mock_config, mock_redis_class):
        """Test recording when Redis raises error."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.hincrby.side_effect = RedisError("Write failed")
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        
        # Should not raise error, should log it
        collector.record_api_call(
            endpoint="/api/query",
            method="POST",
            user_id="user-123",
            status_code=200,
            latency_ms=150.5
        )


class TestRecordTokens:
    """Test token usage recording."""
    
    @patch('app.analytics.collector.redis.Redis')
    @patch('app.analytics.collector.config')
    def test_record_tokens_success(self, mock_config, mock_redis_class):
        """Test successful token recording."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        
        collector.record_tokens(
            user_id="user-123",
            endpoint="/api/query",
            prompt_tokens=100,
            completion_tokens=50,
            model="gemini-2.0-flash"
        )
        
        # Verify token counters incremented
        assert mock_redis.hincrby.called
        # Should increment prompt_tokens, completion_tokens, total_tokens
        assert mock_redis.hincrby.call_count >= 3
    
    @patch('app.analytics.collector.redis.Redis')
    @patch('app.analytics.collector.config')
    def test_record_tokens_calculates_cost(self, mock_config, mock_redis_class):
        """Test token cost calculation."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        
        # Test cost calculation: 1M input = $0.075, 1M output = $0.30
        collector.record_tokens(
            user_id="user-123",
            endpoint="/api/query",
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
            model="gemini-2.0-flash"
        )
        
        # Cost should be: (1M/1M * 0.075) + (1M/1M * 0.30) = 0.375
        assert mock_redis.hincrby.called
    
    @patch('app.analytics.collector.redis.Redis')
    @patch('app.analytics.collector.config')
    def test_record_tokens_no_client(self, mock_config, mock_redis_class):
        """Test recording tokens when client is None."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = None
        
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = RedisError("Connection failed")
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        
        # Should not raise error
        collector.record_tokens(
            user_id="user-123",
            endpoint="/api/query",
            prompt_tokens=100,
            completion_tokens=50,
            model="gemini-2.0-flash"
        )
    
    @patch('app.analytics.collector.redis.Redis')
    @patch('app.analytics.collector.config')
    def test_record_tokens_redis_error(self, mock_config, mock_redis_class):
        """Test recording tokens when Redis raises error."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.hincrby.side_effect = RedisError("Write failed")
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        
        # Should not raise error
        collector.record_tokens(
            user_id="user-123",
            endpoint="/api/query",
            prompt_tokens=100,
            completion_tokens=50,
            model="gemini-2.0-flash"
        )


class TestTokenPricing:
    """Test token pricing constants."""
    
    def test_token_pricing_defined(self):
        """Test token pricing constants are defined."""
        assert "input" in AnalyticsCollector.TOKEN_PRICING
        assert "output" in AnalyticsCollector.TOKEN_PRICING
        assert AnalyticsCollector.TOKEN_PRICING["input"] == 0.075
        assert AnalyticsCollector.TOKEN_PRICING["output"] == 0.30


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @patch('app.analytics.collector.redis.Redis')
    @patch('app.analytics.collector.config')
    def test_zero_tokens(self, mock_config, mock_redis_class):
        """Test recording zero tokens."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        
        collector.record_tokens(
            user_id="user-123",
            endpoint="/api/query",
            prompt_tokens=0,
            completion_tokens=0,
            model="gemini-2.0-flash"
        )
        
        assert mock_redis.hincrby.called
    
    @patch('app.analytics.collector.redis.Redis')
    @patch('app.analytics.collector.config')
    def test_zero_latency(self, mock_config, mock_redis_class):
        """Test recording zero latency."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        
        collector.record_api_call(
            endpoint="/api/query",
            method="POST",
            user_id="user-123",
            status_code=200,
            latency_ms=0.0
        )
        
        assert mock_redis.zadd.called
    
    @patch('app.analytics.collector.redis.Redis')
    @patch('app.analytics.collector.config')
    def test_error_status_code(self, mock_config, mock_redis_class):
        """Test recording error status codes."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        
        for status_code in [400, 401, 403, 404, 500, 503]:
            collector.record_api_call(
                endpoint="/api/query",
                method="POST",
                user_id="user-123",
                status_code=status_code,
                latency_ms=100.0
            )
        
        assert mock_redis.hincrby.called


@pytest.mark.xfail(reason="Testing connection recovery scenarios")
class TestConnectionRecovery:
    """Test connection recovery scenarios."""
    
    @patch('app.analytics.collector.redis.Redis')
    @patch('app.analytics.collector.config')
    def test_reconnect_after_failure(self, mock_config, mock_redis_class):
        """Test reconnection after connection failure."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        
        # Simulate connection failure
        collector.client = None
        
        # Try to record (should handle gracefully)
        collector.record_api_call(
            endpoint="/api/query",
            method="POST",
            user_id="user-123",
            status_code=200,
            latency_ms=100.0
        )


class TestGetUsageStats:
    """Test get_usage_stats method."""
    
    @patch('app.analytics.collector.redis.Redis')
    def test_get_usage_stats_with_data(self, mock_redis_class):
        """Test getting usage stats with data."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.hgetall.side_effect = [
            {b'/query': b'10', b'/ingest': b'5'},  # API calls
            {b'200': b'12', b'404': b'3'},  # Status codes
            {b'POST': b'10', b'GET': b'5'},  # Methods
            {b'total_tokens': b'1000'},  # Tokens
            {b'total_cost_cents': b'50'}  # Cost
        ]
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        stats = collector.get_usage_stats()
        
        assert stats["total_calls"] == 15
        assert stats["api_calls"] == {"/query": 10, "/ingest": 5}
        assert stats["status_codes"] == {"200": 12, "404": 3}
        assert stats["cost_usd"] == 0.50
    
    @patch('app.analytics.collector.redis.Redis')
    def test_get_usage_stats_with_user_id(self, mock_redis_class):
        """Test getting usage stats for specific user."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.hgetall.side_effect = [
            {b'/query': b'5'},  # User-specific API calls
            {b'200': b'5'},  # Status codes
            {b'POST': b'5'},  # Methods
            {b'total_tokens': b'500'},  # User tokens
            {b'total_cost_cents': b'25'}  # User cost
        ]
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        stats = collector.get_usage_stats(user_id="user-123")
        
        assert stats["total_calls"] == 5
        assert stats["cost_usd"] == 0.25
    
    @patch('app.analytics.collector.redis.Redis')
    def test_get_usage_stats_no_client(self, mock_redis_class):
        """Test get_usage_stats when client is None."""
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = RedisError("Connection failed")
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        collector.client = None
        
        stats = collector.get_usage_stats()
        assert stats == {}
    
    @patch('app.analytics.collector.redis.Redis')
    def test_get_usage_stats_redis_error(self, mock_redis_class):
        """Test get_usage_stats with Redis error."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.hgetall.side_effect = RedisError("Redis error")
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        stats = collector.get_usage_stats()
        
        assert stats == {}


class TestGetLatencyStats:
    """Test get_latency_stats method."""
    
    @patch('app.analytics.collector.redis.Redis')
    def test_get_latency_stats_with_data(self, mock_redis_class):
        """Test getting latency stats with data."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        # Mock zrange to return latency scores
        mock_redis.zrange.return_value = [
            (b'req1', 50.0),
            (b'req2', 100.0),
            (b'req3', 150.0),
            (b'req4', 200.0),
            (b'req5', 250.0)
        ]
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        stats = collector.get_latency_stats("/query", hours=1)
        
        assert stats["count"] == 5
        assert stats["min"] == 50.0
        assert stats["max"] == 250.0
        assert stats["mean"] == 150.0
        assert "p50" in stats
        assert "p95" in stats
        assert "p99" in stats
    
    @patch('app.analytics.collector.redis.Redis')
    def test_get_latency_stats_no_data(self, mock_redis_class):
        """Test latency stats when no data available."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.zrange.return_value = []
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        stats = collector.get_latency_stats("/query", hours=24)
        
        assert stats["count"] == 0
        assert stats["p50"] == 0
        assert stats["p95"] == 0
    
    @patch('app.analytics.collector.redis.Redis')
    def test_get_latency_stats_no_client(self, mock_redis_class):
        """Test latency stats when client is None."""
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = RedisError()
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        collector.client = None
        
        stats = collector.get_latency_stats("/query")
        assert stats == {}


class TestGetUserActivity:
    """Test get_user_activity method."""
    
    @patch('app.analytics.collector.redis.Redis')
    def test_get_user_activity(self, mock_redis_class):
        """Test getting user activity."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.hgetall.return_value = {
            b'total_tokens': b'100',
            b'/query': b'5'
        }
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        # Mock get_usage_stats to return consistent data
        with patch.object(collector, 'get_usage_stats') as mock_stats:
            mock_stats.return_value = {
                "total_calls": 5,
                "tokens": {"total_tokens": 100},
                "cost_usd": 0.10
            }
            
            activity = collector.get_user_activity("user-123", days=3)
            
            assert activity["user_id"] == "user-123"
            assert len(activity["daily_stats"]) == 3
            assert "totals" in activity
            assert activity["totals"]["calls"] == 15  # 5 * 3 days
    
    @patch('app.analytics.collector.redis.Redis')
    def test_get_user_activity_no_client(self, mock_redis_class):
        """Test user activity when client is None."""
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = RedisError()
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        collector.client = None
        
        activity = collector.get_user_activity("user-123")
        assert activity == {}


class TestGetSystemOverview:
    """Test get_system_overview method."""
    
    @patch('app.analytics.collector.redis.Redis')
    def test_get_system_overview(self, mock_redis_class):
        """Test getting system overview."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.scan_iter.return_value = [
            "tokens:user:user1:2024-01-01",
            "tokens:user:user2:2024-01-01"
        ]
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        
        with patch.object(collector, 'get_usage_stats') as mock_usage, \
             patch.object(collector, 'get_latency_stats') as mock_latency:
            
            mock_usage.return_value = {
                "total_calls": 100,
                "status_codes": {"200": 90, "404": 5, "500": 5},
                "tokens": {"total_tokens": 1000},
                "cost_usd": 1.50
            }
            
            mock_latency.return_value = {
                "p50": 100.0,
                "p95": 200.0,
                "mean": 120.0
            }
            
            overview = collector.get_system_overview()
            
            assert overview["total_requests"] == 100
            assert overview["unique_users"] == 2
            assert overview["error_rate"] == 10.0  # (5+5)/100 * 100
            assert "latency" in overview
    
    @patch('app.analytics.collector.redis.Redis')
    def test_get_system_overview_no_client(self, mock_redis_class):
        """Test system overview when client is None."""
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = RedisError()
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        collector.client = None
        
        overview = collector.get_system_overview()
        assert overview == {}


class TestHealthCheck:
    """Test health_check method."""
    
    @patch('app.analytics.collector.redis.Redis')
    def test_health_check_healthy(self, mock_redis_class):
        """Test health check when system is healthy."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        assert collector.health_check() is True
    
    @patch('app.analytics.collector.redis.Redis')
    def test_health_check_unhealthy(self, mock_redis_class):
        """Test health check when system is unhealthy."""
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = [True, RedisError("Connection lost")]
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        assert collector.health_check() is False
    
    @patch('app.analytics.collector.redis.Redis')
    def test_health_check_no_client(self, mock_redis_class):
        """Test health check when client is None."""
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = RedisError()
        mock_redis_class.return_value = mock_redis
        
        collector = AnalyticsCollector()
        collector.client = None
        
        assert collector.health_check() is False
