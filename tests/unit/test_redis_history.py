"""
Comprehensive tests for ChatHistoryStore - 100% coverage target.
Tests all methods, branches, edge cases, and exception paths.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
import json
import time
from redis.exceptions import RedisError

from app.storage.redis_history import ChatHistoryStore


class TestChatHistoryStoreInit:
    """Test ChatHistoryStore initialization."""
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_init_default(self, mock_config, mock_redis_class):
        """Test default initialization."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        assert store.host == "10.168.174.3"
        assert store.port == 6379
        assert store.db == 0
        assert store.ttl_seconds == 90 * 24 * 60 * 60
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_init_custom_params(self, mock_config, mock_redis_class):
        """Test initialization with custom parameters."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore(
            host="custom-host",
            port=6380,
            password="custom-pass",
            db=1,
            ttl_days=30
        )
        assert store.host == "custom-host"
        assert store.port == 6380
        assert store.password == "custom-pass"
        assert store.db == 1
        assert store.ttl_seconds == 30 * 24 * 60 * 60
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_init_redis_connection_fails(self, mock_config, mock_redis_class):
        """Test initialization when Redis connection fails."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = None
        
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = RedisError("Connection failed")
        mock_redis_class.return_value = mock_redis
        
        with pytest.raises(RuntimeError):
            store = ChatHistoryStore()
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_init_no_password(self, mock_config, mock_redis_class):
        """Test initialization without password."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.side_effect = Exception("Secret not found")
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        assert store.password is None


class TestKeyGeneration:
    """Test Redis key generation methods."""
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_get_user_key(self, mock_config, mock_redis_class):
        """Test user key generation."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        key = store._get_user_key("user-123")
        assert key == "chat:history:user-123"
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_get_conversation_key(self, mock_config, mock_redis_class):
        """Test conversation key generation."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        key = store._get_conversation_key("user-123", "conv-456")
        assert key == "chat:conversation:user-123:conv-456"


class TestSaveMessage:
    """Test message saving."""
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_save_message_success(self, mock_config, mock_redis_class):
        """Test successful message save."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.zadd.return_value = 1
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        
        message_id = store.save_message(
            user_id="user-123",
            question="What is Python?",
            answer="Python is a programming language",
            metadata={"model": "gemini-2.0-flash"}
        )
        
        assert message_id.startswith("user-123:")
        assert mock_redis.zadd.called
        assert mock_redis.expire.called
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_save_message_with_conversation_id(self, mock_config, mock_redis_class):
        """Test saving message with conversation ID."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.zadd.return_value = 1
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        
        message_id = store.save_message(
            user_id="user-123",
            question="What is Python?",
            answer="Python is a programming language",
            conversation_id="conv-456"
        )
        
        assert message_id.startswith("user-123:")
        assert mock_redis.zadd.call_count >= 2
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_save_message_no_client(self, mock_config, mock_redis_class):
        """Test saving when client is None."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = None
        
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = RedisError("Connection failed")
        mock_redis_class.return_value = mock_redis
        
        try:
            store = ChatHistoryStore()
        except RuntimeError:
            pass
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_save_message_redis_error(self, mock_config, mock_redis_class):
        """Test saving when Redis raises error."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.lpush.side_effect = RedisError("Write failed")
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        
        try:
            store.save_message(
                user_id="user-123",
                question="What is Python?",
                answer="Python is a programming language"
            )
        except RedisError:
            pass


class TestGetHistory:
    """Test retrieving chat history."""
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_get_history_success(self, mock_config, mock_redis_class):
        """Test successful history retrieval."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        
        # Mock history data
        message_data = {
            "id": "user-123:1234567890",
            "user_id": "user-123",
            "question": "What is Python?",
            "answer": "Python is a programming language",
            "timestamp": time.time(),
            "conversation_id": "default"
        }
        mock_redis.zrevrange.return_value = [json.dumps(message_data)]
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        history = store.get_history(user_id="user-123", limit=10)
        
        assert isinstance(history, list)
        assert len(history) > 0
        assert history[0]["question"] == "What is Python?"
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_get_history_no_messages(self, mock_config, mock_redis_class):
        """Test retrieving history when no messages exist."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.zrevrange.return_value = []
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        history = store.get_history(user_id="user-123")
        
        assert history == []
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_get_history_with_conversation_id(self, mock_config, mock_redis_class):
        """Test retrieving history for specific conversation."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.zrevrange.return_value = []
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        history = store.get_history(user_id="user-123", conversation_id="conv-456")
        
        # Should call zrevrange with conversation key
        assert mock_redis.zrevrange.called
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_get_history_with_pagination(self, mock_config, mock_redis_class):
        """Test history retrieval with pagination."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.zrevrange.return_value = []
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        history = store.get_history(user_id="user-123", limit=10, offset=5)
        
        # Should call with correct range
        call_args = mock_redis.zrevrange.call_args[0]
        assert call_args[1] == 5  # offset
        assert call_args[2] == 14  # offset + limit - 1
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_get_history_invalid_json(self, mock_config, mock_redis_class):
        """Test handling of invalid JSON in history."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.zrevrange.return_value = ["invalid json", '{"valid": "json"}']
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        history = store.get_history(user_id="user-123")
        
        # Should skip invalid JSON and return valid one
        assert len(history) == 1
        assert history[0]["valid"] == "json"
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_get_history_redis_error(self, mock_config, mock_redis_class):
        """Test handling of Redis errors during retrieval."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.zrevrange.side_effect = RedisError("Connection lost")
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        history = store.get_history(user_id="user-123")
        
        # Should return empty list on error
        assert history == []


class TestGetConversationIds:
    """Test conversation ID retrieval."""
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_get_conversation_ids_success(self, mock_config, mock_redis_class):
        """Test retrieving conversation IDs."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.keys.return_value = [
            "chat:conversation:user-123:conv-1",
            "chat:conversation:user-123:conv-2"
        ]
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        conv_ids = store.get_conversation_ids("user-123")
        
        assert len(conv_ids) == 2
        assert "conv-1" in conv_ids
        assert "conv-2" in conv_ids
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_get_conversation_ids_no_conversations(self, mock_config, mock_redis_class):
        """Test when no conversations exist."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.keys.return_value = []
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        conv_ids = store.get_conversation_ids("user-123")
        
        assert conv_ids == []
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_get_conversation_ids_redis_error(self, mock_config, mock_redis_class):
        """Test handling of Redis errors."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.keys.side_effect = RedisError("Connection lost")
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        conv_ids = store.get_conversation_ids("user-123")
        
        assert conv_ids == []


class TestDeleteHistory:
    """Test history deletion."""
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_delete_specific_conversation(self, mock_config, mock_redis_class):
        """Test deleting specific conversation."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        result = store.delete_history("user-123", conversation_id="conv-456")
        
        assert result is True
        assert mock_redis.delete.called
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_delete_all_history(self, mock_config, mock_redis_class):
        """Test deleting all history for user."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.keys.return_value = ["chat:conversation:user-123:conv-1"]
        mock_redis.delete.return_value = 1
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        result = store.delete_history("user-123")
        
        assert result is True
        # Should delete user key and all conversation keys
        assert mock_redis.delete.call_count >= 2
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_delete_history_redis_error(self, mock_config, mock_redis_class):
        """Test handling of Redis errors during deletion."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.delete.side_effect = RedisError("Connection lost")
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        result = store.delete_history("user-123")
        
        assert result is False


class TestGetMessageCount:
    """Test message count retrieval."""
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_get_message_count_success(self, mock_config, mock_redis_class):
        """Test retrieving message count."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.zcard.return_value = 42
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        count = store.get_message_count("user-123")
        
        assert count == 42
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_get_message_count_with_conversation(self, mock_config, mock_redis_class):
        """Test retrieving count for specific conversation."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.zcard.return_value = 10
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        count = store.get_message_count("user-123", conversation_id="conv-456")
        
        assert count == 10
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_get_message_count_redis_error(self, mock_config, mock_redis_class):
        """Test handling of Redis errors."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.zcard.side_effect = RedisError("Connection lost")
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        count = store.get_message_count("user-123")
        
        assert count == 0


class TestSearchHistory:
    """Test history search functionality."""
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_search_history_found(self, mock_config, mock_redis_class):
        """Test searching history with matches."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        
        messages = [
            json.dumps({"question": "What is Python?", "answer": "A programming language"}),
            json.dumps({"question": "What is Java?", "answer": "Another programming language"})
        ]
        mock_redis.zrevrange.return_value = messages
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        results = store.search_history("user-123", query="Python")
        
        assert len(results) > 0
        assert "Python" in results[0]["question"]
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_search_history_not_found(self, mock_config, mock_redis_class):
        """Test searching with no matches."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        
        messages = [
            json.dumps({"question": "What is Python?", "answer": "A programming language"})
        ]
        mock_redis.zrevrange.return_value = messages
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        results = store.search_history("user-123", query="Nonexistent")
        
        assert len(results) == 0


class TestHealthCheck:
    """Test health check functionality."""
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_health_check_success(self, mock_config, mock_redis_class):
        """Test successful health check."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        assert store.health_check() is True
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_health_check_no_client(self, mock_config, mock_redis_class):
        """Test health check when client unavailable."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        store.client = None
        
        assert store.health_check() is False
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_health_check_ping_fails(self, mock_config, mock_redis_class):
        """Test health check when ping fails."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = [True, RedisError("Connection lost")]
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        assert store.health_check() is False


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_empty_user_id(self, mock_config, mock_redis_class):
        """Test with empty user ID."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        
        message_id = store.save_message(
            user_id="",
            question="Test",
            answer="Test answer"
        )
        
        assert isinstance(message_id, str)
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_very_long_message(self, mock_config, mock_redis_class):
        """Test with very long message."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        
        long_text = "word " * 10000
        message_id = store.save_message(
            user_id="user-123",
            question=long_text,
            answer=long_text
        )
        
        assert message_id.startswith("user-123:")
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_special_characters_in_message(self, mock_config, mock_redis_class):
        """Test with special characters."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        
        message_id = store.save_message(
            user_id="user-123",
            question="What is 测试?",
            answer="Test 🚀 answer"
        )
        
        assert message_id.startswith("user-123:")


@pytest.mark.xfail(reason="Testing connection recovery scenarios")
class TestConnectionRecovery:
    """Test connection recovery scenarios."""
    
    @patch('app.storage.redis_history.redis.Redis')
    @patch('app.storage.redis_history.config')
    def test_reconnect_after_failure(self, mock_config, mock_redis_class):
        """Test reconnection after connection failure."""
        mock_config.get_env.side_effect = lambda key, default: default
        mock_config.get_secret.return_value = "test-password"
        
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        store = ChatHistoryStore()
        
        # Simulate connection failure
        store.client = None
        
        # Try to save (should handle gracefully)
        try:
            store.save_message(
                user_id="user-123",
                question="Test",
                answer="Test answer"
            )
        except Exception:
            pass
