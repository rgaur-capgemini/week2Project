"""
FinOps API Routes - Week 4
FastAPI routes for cost tracking, budgets, and token usage.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.config import PROJECT_ID, PROJECT_NUMBER
from app.logging_config import get_logger
from google.cloud import firestore

from app.finops.cost_tracker_week4 import CostTracker
from app.finops.budget_alerts_week4 import BudgetAlertsManager, BUDGET_TEMPLATES
from app.finops.token_usage_week4 import TokenUsageTracker

logger = get_logger(__name__)
router = APIRouter(prefix="/finops", tags=["finops_week4"])

# Initialize clients
db = firestore.Client(project=PROJECT_ID)
cost_tracker = CostTracker(PROJECT_ID)
token_tracker = TokenUsageTracker(db)

# Billing account would typically come from config
BILLING_ACCOUNT_ID = None  # Set this if available
if BILLING_ACCOUNT_ID:
    budget_manager = BudgetAlertsManager(PROJECT_ID, BILLING_ACCOUNT_ID)
else:
    budget_manager = None


# Pydantic models
class CreateBudgetRequest(BaseModel):
    budget_name: str
    amount: float = Field(..., gt=0)
    thresholds: List[int] = [50, 75, 90, 100]


class CreateAlertRequest(BaseModel):
    alert_name: str
    alert_type: str
    condition: Dict
    recipients: List[str]


class RecordTokenUsageRequest(BaseModel):
    model_name: str
    input_tokens: int = Field(..., ge=0)
    output_tokens: int = Field(..., ge=0)
    request_type: str = "chat"


# Cost tracking endpoints
@router.get("/costs/current-month")
async def get_current_month_costs():
    """Get costs for the current month."""
    try:
        costs = cost_tracker.get_current_month_costs()
        return costs
    except Exception as e:
        logger.error(f"Error getting current month costs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/costs/by-service")
async def get_service_costs(
    service_name: Optional[str] = Query(None, description="Service name (optional, returns all if not provided)"),
    days: int = Query(30, ge=1, le=365)
):
    """Get costs for a specific service or all services over time."""
    try:
        if service_name:
            costs = cost_tracker.get_cost_by_service(service_name, days)
        else:
            # Return all services
            costs = cost_tracker.get_current_month_costs()
        return costs
    except Exception as e:
        logger.error(f"Error getting service costs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/costs/forecast")
async def get_cost_forecast(
    days_ahead: int = Query(30, ge=1, le=90)
):
    """Get cost forecast for upcoming days."""
    try:
        forecast = cost_tracker.get_cost_forecast(days_ahead)
        return forecast
    except Exception as e:
        logger.error(f"Error getting cost forecast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/costs/anomalies")
async def detect_cost_anomalies(
    days: int = Query(7, ge=1, le=90),
    threshold_percent: float = Query(50.0, ge=0, le=200)
):
    """Detect cost anomalies (admin only)."""
    try:
        anomalies = cost_tracker.get_cost_anomalies(threshold_percent)
        return {
            "anomalies": anomalies,
            "count": len(anomalies),
            "days_analyzed": days
        }
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Token usage endpoints
@router.get("/tokens/vertex-ai")
async def get_vertex_ai_token_usage(
    period: str = Query("current_month", regex="^(current_month|last_month|last_7_days|last_30_days)$"),
    days: int = Query(30, ge=1, le=365)
):
    """Get Vertex AI token usage and costs."""
    try:
        # Map period to days
        period_days_map = {
            "current_month": 30,
            "last_month": 30,
            "last_7_days": 7,
            "last_30_days": 30
        }
        actual_days = period_days_map.get(period, days)
        usage = cost_tracker.get_vertex_ai_token_usage(actual_days)
        return usage
    except Exception as e:
        logger.error(f"Error getting token usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tokens/record")
async def record_token_usage(
    request: RecordTokenUsageRequest
):
    """Record token usage for current user."""
    try:
        user_id = user.get("email", "anonymous")
        
        # Estimate cost
        cost = token_tracker.estimate_cost(
            request.model_name,
            request.input_tokens,
            request.output_tokens
        )
        
        # Record usage
        token_tracker.record_usage(
            user_id=user_id,
            model_name=request.model_name,
            input_tokens=request.input_tokens,
            output_tokens=request.output_tokens,
            cost=cost,
            request_type=request.request_type
        )
        
        return {
            "status": "recorded",
            "estimated_cost": cost
        }
    except Exception as e:
        logger.error(f"Error recording token usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tokens/user-usage")
async def get_user_token_usage(
    days: int = Query(30, ge=1, le=365)
):
    """Get token usage for current user."""
    try:
        user_id = user.get("email")
        usage = token_tracker.get_user_usage(user_id, days)
        return usage
    except Exception as e:
        logger.error(f"Error getting user usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tokens/project-usage")
async def get_project_token_usage(
    days: int = Query(30, ge=1, le=365)
):
    """Get token usage for entire project (admin only)."""
    try:
        usage = token_tracker.get_project_usage(days)
        return usage
    except Exception as e:
        logger.error(f"Error getting project usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tokens/top-users")
async def get_top_token_users(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=100)
):
    """Get top token users (admin only)."""
    try:
        top_users = token_tracker.get_top_users(days, limit)
        return {
            "top_users": top_users,
            "period_days": days
        }
    except Exception as e:
        logger.error(f"Error getting top users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tokens/estimate-cost")
async def estimate_token_cost(
    model_name: str = Query(...),
    input_tokens: int = Query(..., ge=0),
    output_tokens: int = Query(..., ge=0)
):
    """Estimate cost for token usage."""
    try:
        cost = token_tracker.estimate_cost(model_name, input_tokens, output_tokens)
        return {
            "model_name": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": cost
        }
    except Exception as e:
        logger.error(f"Error estimating cost: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tokens/check-limits")
async def check_token_limits():
    """Check if user is approaching usage limits."""
    try:
        user_id = user.get("email")
        limits = token_tracker.check_usage_limits(user_id)
        return limits
    except Exception as e:
        logger.error(f"Error checking limits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Budget management endpoints
@router.post("/budgets")
async def create_budget(
    request: CreateBudgetRequest
):
    """Create a monthly budget (admin only)."""
    if not budget_manager:
        raise HTTPException(
            status_code=503,
            detail="Budget management not available (billing account not configured)"
        )
    
    try:
        budget_id = budget_manager.create_monthly_budget(
            budget_name=request.budget_name,
            amount=request.amount,
            threshold_percentages=request.thresholds
        )
        
        if budget_id:
            return {
                "budget_id": budget_id,
                "status": "created"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create budget")
    except Exception as e:
        logger.error(f"Error creating budget: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/budgets")
async def list_budgets():
    """List all budgets (admin only)."""
    if not budget_manager:
        raise HTTPException(
            status_code=503,
            detail="Budget management not available"
        )
    
    try:
        budgets = budget_manager.list_budgets()
        return {
            "budgets": budgets,
            "count": len(budgets)
        }
    except Exception as e:
        logger.error(f"Error listing budgets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/budgets/templates")
async def get_budget_templates():
    """Get predefined budget templates (admin only)."""
    return {"templates": BUDGET_TEMPLATES}


@router.post("/alerts")
async def create_cost_alert(
    request: CreateAlertRequest
):
    """Create a custom cost alert (admin only)."""
    if not budget_manager:
        raise HTTPException(
            status_code=503,
            detail="Alert management not available"
        )
    
    try:
        alert_id = budget_manager.create_alert(
            alert_name=request.alert_name,
            alert_type=request.alert_type,
            condition=request.condition,
            recipients=request.recipients
        )
        
        return {
            "alert_id": alert_id,
            "status": "created"
        }
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_finops_dashboard():
    """Get comprehensive FinOps dashboard data (admin only)."""
    try:
        # Aggregate data from multiple sources
        current_costs = cost_tracker.get_current_month_costs()
        forecast = cost_tracker.get_cost_forecast(30)
        vertex_usage = cost_tracker.get_vertex_ai_token_usage(30)
        project_tokens = token_tracker.get_project_usage(30)
        anomalies = cost_tracker.get_cost_anomalies(50.0)
        
        return {
            "current_month_costs": current_costs,
            "cost_forecast": forecast,
            "vertex_ai_usage": vertex_usage,
            "token_usage": project_tokens,
            "cost_anomalies": anomalies[:5],  # Top 5 anomalies
            "summary": {
                "total_cost_mtd": current_costs.get("total_cost", 0),
                "forecasted_total": forecast.get("forecasted_total", 0),
                "vertex_ai_tokens": vertex_usage.get("total_tokens", 0),
                "vertex_ai_cost": vertex_usage.get("total_cost", 0),
                "anomaly_count": len(anomalies)
            }
        }
    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# _week4
