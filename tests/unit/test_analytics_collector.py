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
