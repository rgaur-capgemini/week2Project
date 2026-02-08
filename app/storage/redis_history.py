"""
Redis-based chat history storage.
Provides user-specific conversation persistence with TTL and pagination.
"""

import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import redis
from redis import Redis
from redis.exceptions import RedisError

from app.logging_config import get_logger
from app.config import config

logger = get_logger(__name__)


class ChatHistoryStore:
    """
    Redis-based chat history storage.
    
    Features:
    - User-specific history isolation
    - Automatic expiration (TTL)
    - Pagination support
    - Conversation threading
    - Search by timestamp
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        db: int = 0,
        ttl_days: int = 90
    ):
        """
        Initialize chat history store.
        
        Args:
            host: Redis host
            port: Redis port
            password: Redis password (from Secret Manager)
            db: Redis database number
            ttl_days: Days to keep chat history
        """
        self.host = host or config.get_env("REDIS_HOST", "10.168.174.3")
        self.port = port or int(config.get_env("REDIS_PORT", "6379"))
        self.db = db
        self.ttl_seconds = ttl_days * 24 * 60 * 60
        
        # Get password from Secret Manager if configured
        self.password = password
        if not self.password:
            try:
                self.password = config.get_secret("redis-password")
            except Exception:
                logger.warning("Redis password not configured - using no auth")
                self.password = None
        
        # Initialize Redis connection
        self.client: Optional[Redis] = None
        self._connect()
    
    def _connect(self):
        """Establish Redis connection with retry logic."""
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self.client.ping()
            
            logger.info(
                "Redis connection established",
                host=self.host,
                port=self.port,
                db=self.db
            )
        except RedisError as e:
            logger.error(f"Redis connection failed: {e}")
            self.client = None
            raise RuntimeError(f"Could not connect to Redis: {e}")
    
    def _get_user_key(self, user_id: str) -> str:
        """Generate Redis key for user's chat history."""
        return f"chat:history:{user_id}"
    
    def _get_conversation_key(self, user_id: str, conversation_id: str) -> str:
        """Generate Redis key for specific conversation."""
        return f"chat:conversation:{user_id}:{conversation_id}"
    
    def save_message(
        self,
        user_id: str,
        question: str,
        answer: str,
        metadata: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None
    ) -> str:
        """
        Save a chat message to history.
        
        Args:
            user_id: User identifier
            question: User's question
            answer: Assistant's answer
            metadata: Additional metadata (model, tokens, latency, etc.)
            conversation_id: Optional conversation thread ID
        
        Returns:
            Message ID
        """
        if not self.client:
            logger.warning("Redis client not available")
            return ""
        
        try:
            timestamp = time.time()
            message_id = f"{user_id}:{int(timestamp * 1000)}"
            
            # Build message object
            message = {
                "id": message_id,
                "user_id": user_id,
                "question": question,
                "answer": answer,
                "timestamp": timestamp,
                "datetime": datetime.fromtimestamp(timestamp).isoformat(),
                "conversation_id": conversation_id or "default",
                "metadata": metadata or {}
            }
            
            # Store in user's history (sorted set by timestamp)
            user_key = self._get_user_key(user_id)
            self.client.zadd(user_key, {json.dumps(message): timestamp})
            
            # Set TTL
            self.client.expire(user_key, self.ttl_seconds)
            
            # Also store in conversation-specific key if provided
            if conversation_id:
                conv_key = self._get_conversation_key(user_id, conversation_id)
                self.client.zadd(conv_key, {json.dumps(message): timestamp})
                self.client.expire(conv_key, self.ttl_seconds)
            
            logger.info(
                "Chat message saved",
                user_id=user_id,
                message_id=message_id,
                conversation_id=conversation_id
            )
            
            return message_id
            
        except RedisError as e:
            logger.error(f"Failed to save chat message: {e}")
            return ""
    
    def get_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        conversation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve user's chat history.
        
        Args:
            user_id: User identifier
            limit: Maximum number of messages to return
            offset: Number of messages to skip (for pagination)
            conversation_id: Optional conversation filter
        
        Returns:
            List of chat messages (newest first)
        """
        if not self.client:
            logger.warning("Redis client not available")
            return []
        
        try:
            # Choose key based on conversation filter
            if conversation_id:
                key = self._get_conversation_key(user_id, conversation_id)
            else:
                key = self._get_user_key(user_id)
            
            # Get messages in reverse chronological order
            start = offset
            end = offset + limit - 1
            messages = self.client.zrevrange(key, start, end)
            
            # Parse JSON messages
            parsed_messages = []
            for msg_json in messages:
                try:
                    parsed_messages.append(json.loads(msg_json))
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse message: {e}")
            
            logger.info(
                "Retrieved chat history",
                user_id=user_id,
                num_messages=len(parsed_messages),
                conversation_id=conversation_id
            )
            
            return parsed_messages
            
        except RedisError as e:
            logger.error(f"Failed to retrieve chat history: {e}")
            return []
    
    def get_conversation_ids(self, user_id: str) -> List[str]:
        """
        Get all conversation IDs for a user.
        
        Args:
            user_id: User identifier
        
        Returns:
            List of conversation IDs
        """
        if not self.client:
            return []
        
        try:
            pattern = f"chat:conversation:{user_id}:*"
            keys = self.client.keys(pattern)
            
            # Extract conversation IDs from keys
            conv_ids = []
            for key in keys:
                # Key format: chat:conversation:{user_id}:{conversation_id}
                parts = key.split(":")
                if len(parts) >= 4:
                    conv_ids.append(parts[3])
            
            return sorted(set(conv_ids))
            
        except RedisError as e:
            logger.error(f"Failed to get conversation IDs: {e}")
            return []
    
    def delete_history(
        self,
        user_id: str,
        conversation_id: Optional[str] = None
    ) -> bool:
        """
        Delete user's chat history.
        
        Args:
            user_id: User identifier
            conversation_id: Optional conversation to delete (deletes all if None)
        
        Returns:
            True if successful
        """
        if not self.client:
            return False
        
        try:
            if conversation_id:
                # Delete specific conversation
                key = self._get_conversation_key(user_id, conversation_id)
                self.client.delete(key)
                logger.info(
                    "Deleted conversation",
                    user_id=user_id,
                    conversation_id=conversation_id
                )
            else:
                # Delete all conversations for user
                user_key = self._get_user_key(user_id)
                pattern = f"chat:conversation:{user_id}:*"
                
                self.client.delete(user_key)
                
                # Delete all conversation keys
                for key in self.client.keys(pattern):
                    self.client.delete(key)
                
                logger.info("Deleted all history", user_id=user_id)
            
            return True
            
        except RedisError as e:
            logger.error(f"Failed to delete history: {e}")
            return False
    
    def get_message_count(
        self,
        user_id: str,
        conversation_id: Optional[str] = None
    ) -> int:
        """
        Get total message count for user.
        
        Args:
            user_id: User identifier
            conversation_id: Optional conversation filter
        
        Returns:
            Number of messages
        """
        if not self.client:
            return 0
        
        try:
            if conversation_id:
                key = self._get_conversation_key(user_id, conversation_id)
            else:
                key = self._get_user_key(user_id)
            
            return self.client.zcard(key)
            
        except RedisError as e:
            logger.error(f"Failed to get message count: {e}")
            return 0
    
    def search_history(
        self,
        user_id: str,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search chat history by keyword.
        
        Args:
            user_id: User identifier
            query: Search query
            limit: Maximum results
        
        Returns:
            Matching messages
        """
        # Simple implementation - retrieves all and filters
        # For production, consider Redis Search module
        all_messages = self.get_history(user_id, limit=1000)
        
        query_lower = query.lower()
        matches = []
        
        for msg in all_messages:
            question = msg.get("question", "").lower()
            answer = msg.get("answer", "").lower()
            
            if query_lower in question or query_lower in answer:
                matches.append(msg)
                
                if len(matches) >= limit:
                    break
        
        logger.info(
            "Search completed",
            user_id=user_id,
            query=query,
            num_results=len(matches)
        )
        
        return matches
    
    def health_check(self) -> bool:
        """Check if Redis connection is healthy."""
        if not self.client:
            return False
        
        try:
            self.client.ping()
            return True
        except RedisError:
            return False
