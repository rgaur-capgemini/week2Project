"""
New API Routes for Authentication, History, and Analytics.
These endpoints extend the main application.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from app.auth.oidc import get_current_user, get_optional_user
from app.auth.rbac import get_rbac_manager, Permission, Role
from app.storage.redis_history import ChatHistoryStore
from app.analytics.collector import AnalyticsCollector
from app.logging_config import get_logger

logger = get_logger(__name__)

# Create routers
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
history_router = APIRouter(prefix="/history", tags=["Chat History"])
analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ==================== Schemas ====================

class LoginRequest(BaseModel):
    """Google OAuth login request."""
    token: str = Field(..., description="Google OAuth ID token")


class LoginResponse(BaseModel):
    """Login response with user info and access token."""
    user_id: str
    email: str
    name: Optional[str]
    role: str
    access_token: str
    refresh_token: Optional[str]
    expires_in: int


class UserInfo(BaseModel):
    """User information response."""
    user_id: str
    email: str
    name: Optional[str]
    role: str
    permissions: List[str]


class ChatHistoryQuery(BaseModel):
    """Query for chat history."""
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)
    conversation_id: Optional[str] = None


class ChatMessage(BaseModel):
    """Single chat message."""
    id: str
    question: str
    answer: str
    timestamp: float
    datetime: str
    conversation_id: str
    metadata: Dict[str, Any] = {}


class HistoryResponse(BaseModel):
    """Chat history response."""
    user_id: str
    messages: List[ChatMessage]
    total_count: int
    has_more: bool


class ConversationListResponse(BaseModel):
    """List of conversations."""
    user_id: str
    conversations: List[str]


class AnalyticsQuery(BaseModel):
    """Analytics query parameters."""
    date: Optional[str] = Field(None, description="Date (YYYY-MM-DD)")
    user_id: Optional[str] = None
    days: int = Field(7, ge=1, le=90)


class UsageStats(BaseModel):
    """Usage statistics."""
    date: str
    total_calls: int
    api_calls: Dict[str, int]
    status_codes: Dict[str, int]
    methods: Dict[str, int]
    tokens: Dict[str, int]
    cost_usd: float


class LatencyStats(BaseModel):
    """Latency statistics."""
    endpoint: str
    p50: float
    p95: float
    p99: float
    mean: float
    max: float
    min: float
    count: int


class SystemOverview(BaseModel):
    """System-wide analytics."""
    date: str
    total_requests: int
    unique_users: int
    error_rate: float
    total_tokens: int
    total_cost_usd: float
    latency: Dict[str, Any]
    status_distribution: Dict[str, int]


# ==================== Dependencies ====================

# Global instances (initialized in main.py lifespan)
chat_history_store: Optional[ChatHistoryStore] = None
analytics_collector: Optional[AnalyticsCollector] = None


def get_chat_history_store() -> ChatHistoryStore:
    """Get chat history store instance."""
    if chat_history_store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat history service not available"
        )
    return chat_history_store


def get_analytics_collector() -> AnalyticsCollector:
    """Get analytics collector instance."""
    if analytics_collector is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service not available"
        )
    return analytics_collector


# ==================== Authentication Endpoints ====================

@auth_router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login with Google OAuth token.
    Validates token and returns user info with access token.
    """
    from app.auth.oidc import OIDCAuthenticator
    from app.auth.jwt_handler import JWTHandler
    from app.auth.rbac import get_rbac_manager
    
    try:
        authenticator = OIDCAuthenticator()
        jwt_handler = JWTHandler()
        rbac = get_rbac_manager()
        
        # Validate Google OAuth token
        user_info = await authenticator.validate_google_token(request.token)
        
        # Determine user role
        role = rbac.get_user_role(user_info)
        
        # Create access and refresh tokens
        access_token = jwt_handler.create_access_token(
            user_id=user_info["user_id"],
            email=user_info["email"],
            role=role.value
        )
        
        refresh_token = jwt_handler.create_refresh_token(
            user_id=user_info["user_id"],
            email=user_info["email"]
        )
        
        logger.info(
            "User logged in",
            user_id=user_info["user_id"],
            email=user_info["email"],
            role=role.value
        )
        
        return LoginResponse(
            user_id=user_info["user_id"],
            email=user_info["email"],
            name=user_info.get("name"),
            role=role.value,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=jwt_handler.access_token_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login failed"
        )


@auth_router.get("/me", response_model=UserInfo)
async def get_me(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get current user information.
    Requires authentication.
    """
    rbac = get_rbac_manager()
    role = rbac.get_user_role(user)
    permissions = [p.value for p in rbac.get_permissions(role)]
    
    return UserInfo(
        user_id=user["user_id"],
        email=user["email"],
        name=user.get("name"),
        role=role.value,
        permissions=permissions
    )


@auth_router.post("/refresh")
async def refresh_token(refresh_token: str):
    """
    Refresh access token using refresh token.
    """
    from app.auth.jwt_handler import JWTHandler
    from app.auth.rbac import get_rbac_manager
    
    try:
        jwt_handler = JWTHandler()
        rbac = get_rbac_manager()
        
        # Decode refresh token
        payload = jwt_handler.decode_token(refresh_token)
        
        # Verify it's a refresh token
        if payload.get("token_type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )
        
        # Create new access token with role
        # Note: Role might have changed, but we use stored role for security
        user_info = {"user_id": payload["user_id"], "email": payload["email"]}
        role = rbac.get_user_role(user_info)
        
        new_access_token = jwt_handler.create_access_token(
            user_id=payload["user_id"],
            email=payload["email"],
            role=role.value
        )
        
        return {
            "access_token": new_access_token,
            "expires_in": jwt_handler.access_token_expire_minutes * 60
        }
        
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


# ==================== Chat History Endpoints ====================

@history_router.get("/", response_model=HistoryResponse)
async def get_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    conversation_id: Optional[str] = None,
    user: Dict[str, Any] = Depends(get_current_user),
    history_store: ChatHistoryStore = Depends(get_chat_history_store)
):
    """
    Get user's chat history.
    Paginated results, newest first.
    """
    rbac = get_rbac_manager()
    rbac.require_permission(user, Permission.CHAT_VIEW_HISTORY)
    
    user_id = user["user_id"]
    
    # Retrieve history
    messages = history_store.get_history(
        user_id=user_id,
        limit=limit,
        offset=offset,
        conversation_id=conversation_id
    )
    
    # Get total count
    total_count = history_store.get_message_count(
        user_id=user_id,
        conversation_id=conversation_id
    )
    
    has_more = (offset + len(messages)) < total_count
    
    # Convert to response model
    chat_messages = [ChatMessage(**msg) for msg in messages]
    
    return HistoryResponse(
        user_id=user_id,
        messages=chat_messages,
        total_count=total_count,
        has_more=has_more
    )


@history_router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(
    user: Dict[str, Any] = Depends(get_current_user),
    history_store: ChatHistoryStore = Depends(get_chat_history_store)
):
    """Get list of user's conversation IDs."""
    rbac = get_rbac_manager()
    rbac.require_permission(user, Permission.CHAT_VIEW_HISTORY)
    
    user_id = user["user_id"]
    conversations = history_store.get_conversation_ids(user_id)
    
    return ConversationListResponse(
        user_id=user_id,
        conversations=conversations
    )


@history_router.delete("/")
async def delete_history(
    conversation_id: Optional[str] = None,
    user: Dict[str, Any] = Depends(get_current_user),
    history_store: ChatHistoryStore = Depends(get_chat_history_store)
):
    """Delete user's chat history."""
    rbac = get_rbac_manager()
    rbac.require_permission(user, Permission.CHAT_DELETE_HISTORY)
    
    user_id = user["user_id"]
    
    success = history_store.delete_history(
        user_id=user_id,
        conversation_id=conversation_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete history"
        )
    
    return {
        "status": "success",
        "message": f"History deleted for user {user_id}",
        "conversation_id": conversation_id
    }


@history_router.get("/search")
async def search_history(
    query: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    user: Dict[str, Any] = Depends(get_current_user),
    history_store: ChatHistoryStore = Depends(get_chat_history_store)
):
    """Search chat history by keyword."""
    rbac = get_rbac_manager()
    rbac.require_permission(user, Permission.CHAT_VIEW_HISTORY)
    
    user_id = user["user_id"]
    
    results = history_store.search_history(
        user_id=user_id,
        query=query,
        limit=limit
    )
    
    return {
        "query": query,
        "results": results,
        "count": len(results)
    }


# ==================== Analytics Endpoints ====================

@analytics_router.get("/usage", response_model=UsageStats)
async def get_usage(
    date: Optional[str] = None,
    user: Dict[str, Any] = Depends(get_current_user),
    analytics: AnalyticsCollector = Depends(get_analytics_collector)
):
    """
    Get usage statistics.
    Admins can view all; users see only their own data.
    """
    rbac = get_rbac_manager()
    rbac.require_permission(user, Permission.ANALYTICS_VIEW)
    
    # Admins can see system-wide stats, users see only their own
    is_admin = rbac.is_admin(user)
    user_id = None if is_admin else user["user_id"]
    
    stats = analytics.get_usage_stats(date=date, user_id=user_id)
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No usage data found"
        )
    
    return UsageStats(
        date=date or datetime.now().strftime("%Y-%m-%d"),
        total_calls=stats.get("total_calls", 0),
        api_calls=stats.get("api_calls", {}),
        status_codes=stats.get("status_codes", {}),
        methods=stats.get("methods", {}),
        tokens=stats.get("tokens", {}),
        cost_usd=stats.get("cost_usd", 0.0)
    )


@analytics_router.get("/latency/{endpoint}", response_model=LatencyStats)
async def get_latency(
    endpoint: str,
    hours: int = Query(1, ge=1, le=24),
    user: Dict[str, Any] = Depends(get_current_user),
    analytics: AnalyticsCollector = Depends(get_analytics_collector)
):
    """Get latency statistics for an endpoint."""
    rbac = get_rbac_manager()
    rbac.require_permission(user, Permission.ANALYTICS_VIEW)
    
    # Ensure endpoint starts with /
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"
    
    stats = analytics.get_latency_stats(endpoint=endpoint, hours=hours)
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No latency data found"
        )
    
    # Build LatencyStats with explicit type casting for count
    return LatencyStats(
        endpoint=endpoint,
        p50=stats["p50"],
        p95=stats["p95"],
        p99=stats["p99"],
        mean=stats["mean"],
        max=stats["max"],
        min=stats["min"],
        count=int(stats["count"])
    )


@analytics_router.get("/overview", response_model=SystemOverview)
async def get_system_overview(
    user: Dict[str, Any] = Depends(get_current_user),
    analytics: AnalyticsCollector = Depends(get_analytics_collector)
):
    """
    Get system-wide analytics overview.
    Admin only.
    """
    rbac = get_rbac_manager()
    rbac.require_role(user, Role.ADMIN)
    
    overview = analytics.get_system_overview()
    
    if not overview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No analytics data available"
        )
    
    return SystemOverview(**overview)


@analytics_router.get("/user/{user_id}/activity")
async def get_user_activity(
    user_id: str,
    days: int = Query(7, ge=1, le=90),
    user: Dict[str, Any] = Depends(get_current_user),
    analytics: AnalyticsCollector = Depends(get_analytics_collector)
):
    """
    Get user activity summary.
    Users can view their own; admins can view any user.
    """
    rbac = get_rbac_manager()
    
    # Check permissions
    if not rbac.is_admin(user) and user["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own activity"
        )
    
    rbac.require_permission(user, Permission.ANALYTICS_VIEW)
    
    activity = analytics.get_user_activity(user_id=user_id, days=days)
    
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No activity data found"
        )
    
    return activity


# Export routers
__all__ = [
    "auth_router",
    "history_router",
    "analytics_router",
    "chat_history_store",
    "analytics_collector"
]
