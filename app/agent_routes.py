"""
Agent API Routes - Week 5
FastAPI endpoints for agent interactions.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.agents import AgentOrchestrator, AgentMemory
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])

# Lazy initialization to avoid GCP credential errors at import time
_orchestrator = None
_memory = None

def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator

def get_memory():
    global _memory
    if _memory is None:
        _memory = AgentMemory()
    return _memory


class ChatRequest(BaseModel):
    """Agent chat request"""
    message: str = Field(..., description="User message")
    session_id: str = Field(..., description="Conversation session ID")
    max_iterations: Optional[int] = Field(5, description="Max tool call iterations", ge=1, le=10)


class ChatResponse(BaseModel):
    """Agent chat response"""
    answer: str
    session_id: str
    iterations: int
    execution_trace: List[Dict[str, Any]]
    warning: Optional[str] = None


class HistoryResponse(BaseModel):
    """Conversation history"""
    session_id: str
    messages: List[Dict[str, Any]]


class ToolInfo(BaseModel):
    """Tool information"""
    name: str
    description: str


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(request: ChatRequest):
    """
    Chat with the AI agent. Agent can use tools to answer questions.
    
    Tools available:
    - rag_search: Search knowledge base
    - calculator: Mathematical calculations
    - csv_query: Query CSV data in BigQuery
    - image_analysis: Analyze images with Gemini Vision
    - web_search: Search the internet
    """
    try:
        logger.info(f"Agent chat request: session={request.session_id}")
        
        orchestrator = get_orchestrator()
        result = await orchestrator.chat(
            message=request.message,
            session_id=request.session_id,
            max_iterations=request.max_iterations
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        logger.error(f"Agent chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str, limit: int = 10):
    """Get conversation history for a session"""
    try:
        memory = get_memory()
        messages = await memory.get_history(session_id, limit=limit)
        return HistoryResponse(session_id=session_id, messages=messages)
        
    except Exception as e:
        logger.error(f"Get history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """Clear conversation history for a session"""
    try:
        memory = get_memory()
        await memory.clear_history(session_id)
        return {"message": f"History cleared for session {session_id}"}
        
    except Exception as e:
        logger.error(f"Clear history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_sessions(limit: int = 20):
    """List recent conversation sessions"""
    try:
        memory = get_memory()
        sessions = await memory.list_sessions(limit=limit)
        return {"sessions": sessions, "count": len(sessions)}
        
    except Exception as e:
        logger.error(f"List sessions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools", response_model=List[ToolInfo])
async def get_tools():
    """Get list of available agent tools"""
    try:
        orchestrator = get_orchestrator()
        tools = orchestrator.get_available_tools()
        return [ToolInfo(**tool) for tool in tools]
        
    except Exception as e:
        logger.error(f"Get tools failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
