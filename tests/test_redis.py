"""
Comprehensive test suite for Redis chat history.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from app.storage.redis_store import RedisChatHistory


class TestRedisChatHistory:
    """Test Redis chat history functionality."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        with patch('app.storage.redis_store.redis.Redis') as mock:
            redis_client = MagicMock()
            mock.return_value = redis_client
            redis_client.ping.return_value = True
            yield redis_client
    
    @pytest.fixture
    def chat_history(self, mock_redis):
        """Create RedisChatHistory instance with mocked Redis."""
        return RedisChatHistory(host='localhost', port=6379)
    
    def test_initialization_success(self, mock_redis):
        """Test successful Redis connection."""
        history = RedisChatHistory()
        assert history.client is not None
        mock_redis.ping.assert_called_once()
    
    def test_create_session(self, chat_history, mock_redis):
        """Test creating a new chat session."""
        session_id = chat_history.create_session('user@example.com', 'Initial message')
        
        assert session_id is not None
        assert len(session_id) > 0
        mock_redis.hset.assert_called()
        mock_redis.zadd.assert_called()
    
    def test_add_message(self, chat_history, mock_redis):
        """Test adding a message to a session."""
        session_id = 'test-session-123'
        
        chat_history.add_message(
            session_id=session_id,
            role='user',
            content='Test message',
            metadata={'tokens': 50}
        )
        
        mock_redis.rpush.assert_called()
        mock_redis.hincrby.assert_called()
    
    def test_get_session_history(self, chat_history, mock_redis):
        """Test retrieving session history."""
        session_id = 'test-session-123'
        mock_redis.lrange.return_value = [
            '{"role": "user", "content": "Hello", "timestamp": "2024-01-01T00:00:00"}',
            '{"role": "assistant", "content": "Hi", "timestamp": "2024-01-01T00:00:01"}'
        ]
        
        messages = chat_history.get_session_history(session_id)
        
        assert len(messages) == 2
        assert messages[0]['role'] == 'user'
        assert messages[1]['role'] == 'assistant'
    
    def test_get_user_sessions(self, chat_history, mock_redis):
        """Test retrieving all sessions for a user."""
        mock_redis.zrevrange.return_value = ['session-1', 'session-2']
        mock_redis.hgetall.side_effect = [
            {'session_id': 'session-1', 'title': 'Chat 1'},
            {'session_id': 'session-2', 'title': 'Chat 2'}
        ]
        
        sessions = chat_history.get_user_sessions('user@example.com', limit=10)
        
        assert len(sessions) == 2
        assert sessions[0]['session_id'] == 'session-1'
    
    def test_delete_session(self, chat_history, mock_redis):
        """Test deleting a session."""
        session_id = 'test-session-123'
        user_id = 'user@example.com'
        
        chat_history.delete_session(session_id, user_id)
        
        mock_redis.zrem.assert_called()
        assert mock_redis.delete.call_count == 2  # session key and messages key
    
    def test_get_recent_context(self, chat_history, mock_redis):
        """Test getting recent context for queries."""
        session_id = 'test-session-123'
        mock_redis.lrange.return_value = [
            '{"role": "user", "content": "Recent question", "timestamp": "2024-01-01T00:00:00"}'
        ]
        
        context = chat_history.get_recent_context(session_id, max_messages=5)
        
        assert len(context) == 1
        assert context[0]['content'] == 'Recent question'
    
    def test_update_session_title(self, chat_history, mock_redis):
        """Test updating session title."""
        session_id = 'test-session-123'
        new_title = 'Updated Title'
        
        chat_history.update_session_title(session_id, new_title)
        
        mock_redis.hset.assert_called_with(
            f'chat:session:{session_id}',
            'title',
            new_title
        )
    
    def test_get_stats(self, chat_history, mock_redis):
        """Test getting user statistics."""
        mock_redis.zcard.return_value = 5
        mock_redis.zrange.return_value = ['session-1', 'session-2']
        mock_redis.hget.side_effect = ['10', '15']
        
        stats = chat_history.get_stats('user@example.com')
        
        assert stats['total_sessions'] == 5
        assert stats['total_messages'] == 25
        assert stats['user_id'] == 'user@example.com'


# Run with: pytest tests/test_redis.py -v --cov=app/storage/redis_store
