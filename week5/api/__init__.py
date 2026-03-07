"""
Week 5 - API module.
"""

from week5.api.agent_routes import agent_router, rag_router
from week5.api.multimodal_routes import multimodal_router

__all__ = ["agent_router", "rag_router", "multimodal_router"]
