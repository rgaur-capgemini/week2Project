"""
Redis integration for chat history management.
Stores conversation history with user-specific segregation.
"""

import json
import redis
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.logging_config import get_logger
import os

logger = get_logger(__name__)


class RedisChatHistory:
    """Manages chat history in Redis."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ttl_days: int = 30
    ):
        """
        Initialize Redis connection.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (optional)
            ttl_days: Number of days to keep chat history
        """
        self.ttl_seconds = ttl_days * 24 * 60 * 60
        
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )
            # Test connection
            self.client.ping()
            logger.info("Redis connection established", host=host, port=port)
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise
    
    def _get_user_key(self, user_id: str) -> str:
        """Generate Redis key for user's chat list."""
        return f"chat:user:{user_id}:sessions"
    
    def _get_session_key(self, session_id: str) -> str:
        """Generate Redis key for a specific chat session."""
        return f"chat:session:{session_id}"
    
    def create_session(self, user_id: str, initial_message: Optional[str] = None) -> str:
        """
        Create a new chat session.
        
        Args:
            user_id: User identifier (email or sub)
            initial_message: Optional initial message
            
        Returns:
            session_id: Unique session identifier
        """
        import uuid
        session_id = str(uuid.uuid4())
        
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'message_count': 0,
            'title': initial_message[:50] if initial_message else "New Chat"
        }
        
        # Store session metadata
        session_key = self._get_session_key(session_id)
        self.client.hset(session_key, mapping=session_data)
        self.client.expire(session_key, self.ttl_seconds)
        
        # Add session to user's session list
        user_key = self._get_user_key(user_id)
        self.client.zadd(
            user_key,
            {session_id: datetime.utcnow().timestamp()}
        )
        self.client.expire(user_key, self.ttl_seconds)
        
        logger.info("Chat session created", user_id=user_id, session_id=session_id)
        return session_id
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a message to a chat session.
        
        Args:
            session_id: Session identifier
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional metadata (tokens, latency, etc.)
        """
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        
        # Add message to session's message list
        messages_key = f"{self._get_session_key(session_id)}:messages"
        self.client.rpush(messages_key, json.dumps(message))
        self.client.expire(messages_key, self.ttl_seconds)
        
        # Update session metadata
        session_key = self._get_session_key(session_id)
        self.client.hincrby(session_key, 'message_count', 1)
        self.client.hset(session_key, 'updated_at', datetime.utcnow().isoformat())
        self.client.expire(session_key, self.ttl_seconds)
        
        logger.debug(
            "Message added to session",
            session_id=session_id,
            role=role,
            content_length=len(content)
        )
    
    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all messages in a chat session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of messages with role, content, timestamp
        """
        messages_key = f"{self._get_session_key(session_id)}:messages"
        raw_messages = self.client.lrange(messages_key, 0, -1)
        
        messages = [json.loads(msg) for msg in raw_messages]
        logger.debug("Retrieved session history", session_id=session_id, message_count=len(messages))
        return messages
    
    def get_user_sessions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all chat sessions for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of sessions to return
            offset: Offset for pagination
            
        Returns:
            List of session metadata
        """
        user_key = self._get_user_key(user_id)
        
        # Get session IDs sorted by timestamp (newest first)
        session_ids = self.client.zrevrange(
            user_key,
            offset,
            offset + limit - 1
        )
        
        sessions = []
        for session_id in session_ids:
            session_key = self._get_session_key(session_id)
            session_data = self.client.hgetall(session_key)
            if session_data:
                sessions.append(session_data)
        
        logger.debug("Retrieved user sessions", user_id=user_id, session_count=len(sessions))
        return sessions
    
    def delete_session(self, session_id: str, user_id: str):
        """
        Delete a chat session.
        
        Args:
            session_id: Session identifier
            user_id: User identifier (for authorization)
        """
        # Remove session from user's list
        user_key = self._get_user_key(user_id)
        self.client.zrem(user_key, session_id)
        
        # Delete session data
        session_key = self._get_session_key(session_id)
        messages_key = f"{session_key}:messages"
        
        self.client.delete(session_key)
        self.client.delete(messages_key)
        
        logger.info("Session deleted", session_id=session_id, user_id=user_id)
    
    def get_recent_context(
        self,
        session_id: str,
        max_messages: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent messages for context in new queries.
        
        Args:
            session_id: Session identifier
            max_messages: Maximum number of recent messages
            
        Returns:
            List of recent messages
        """
        messages_key = f"{self._get_session_key(session_id)}:messages"
        raw_messages = self.client.lrange(messages_key, -max_messages, -1)
        
        messages = [json.loads(msg) for msg in raw_messages]
        return messages
    
    def update_session_title(self, session_id: str, title: str):
        """Update the title of a chat session."""
        session_key = self._get_session_key(session_id)
        self.client.hset(session_key, 'title', title)
        logger.debug("Session title updated", session_id=session_id, title=title)
    
    def get_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get chat statistics for a user.
        
        Returns:
            Statistics including total sessions, total messages
        """
        user_key = self._get_user_key(user_id)
        total_sessions = self.client.zcard(user_key)
        
        # Get message count across all sessions
        session_ids = self.client.zrange(user_key, 0, -1)
        total_messages = 0
        
        for session_id in session_ids:
            session_key = self._get_session_key(session_id)
            count = self.client.hget(session_key, 'message_count')
            if count:
                total_messages += int(count)
        
        return {
            'total_sessions': total_sessions,
            'total_messages': total_messages,
            'user_id': user_id
        }


def get_redis_client() -> RedisChatHistory:
    """Factory function to create Redis client from environment."""
    return RedisChatHistory(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        password=os.getenv("REDIS_PASSWORD"),
        ttl_days=int(os.getenv("CHAT_HISTORY_TTL_DAYS", "30"))
    )
