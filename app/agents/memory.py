"""
Agent Memory - Week 5
Store and retrieve conversation history from Firestore.
"""

from typing import List, Dict, Optional
from datetime import datetime
from google.cloud import firestore
from app.logging_config import get_logger

logger = get_logger(__name__)


class AgentMemory:
    """Manage agent conversation history in Firestore"""
    
    def __init__(self):
        self.db = firestore.Client()
        self.collection = "agent_memory"
        logger.info("Agent memory initialized")
    
    async def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the conversation history"""
        try:
            doc_ref = self.db.collection(self.collection).document(session_id)
            
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            # Get or create session
            doc = doc_ref.get()
            if doc.exists:
                # Append to messages array
                doc_ref.update({
                    "messages": firestore.ArrayUnion([message]),
                    "updated_at": datetime.utcnow().isoformat()
                })
            else:
                # Create new session
                doc_ref.set({
                    "session_id": session_id,
                    "messages": [message],
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                })
            
            logger.info(f"Added message to session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            raise
    
    async def get_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Get conversation history for a session"""
        try:
            doc_ref = self.db.collection(self.collection).document(session_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return []
            
            data = doc.to_dict()
            messages = data.get("messages", [])
            
            # Return last N messages
            return messages[-limit:] if messages else []
            
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []
    
    async def clear_history(self, session_id: str):
        """Clear conversation history for a session"""
        try:
            doc_ref = self.db.collection(self.collection).document(session_id)
            doc_ref.delete()
            logger.info(f"Cleared history for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
            raise
    
    async def list_sessions(self, limit: int = 20) -> List[Dict]:
        """List recent sessions"""
        try:
            sessions = []
            query = (
                self.db.collection(self.collection)
                .order_by("updated_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )
            
            for doc in query.stream():
                data = doc.to_dict()
                sessions.append({
                    "session_id": data.get("session_id"),
                    "message_count": len(data.get("messages", [])),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at")
                })
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []
