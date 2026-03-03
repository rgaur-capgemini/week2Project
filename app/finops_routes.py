"""
FinOps dashboard API endpoints.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any, List
from app.auth.rbac import require_role
from app.finops.cost_tracker import FinOpsTracker
from app.config import Config

config = Config()
finops_router = APIRouter(prefix="/finops", tags=["finops"])


class CostSummary(BaseModel):
    """Cost summary response."""
    total_cost_usd: float
    by_service: Dict[str, float]
    token_costs: Dict[str, Any]
    budget_status: Dict[str, Any]


class CostAnomaly(BaseModel):
    """Cost anomaly alert."""
    service: str
    current_cost: float
    baseline_cost: float
    increase_percent: float
    reason: str
    recommendation: str


@finops_router.get("/dashboard", response_model=CostSummary)
@require_role("admin")
async def get_finops_dashboard():
    """
    Get FinOps dashboard data (admin only).
    
    Returns:
    - Current month costs by service
    - Token usage and costs
    - Budget status and alerts
    - Cost anomalies
    """
    tracker = FinOpsTracker(
        project_id=config.PROJECT_ID,
        billing_account_id=getattr(config, 'BILLING_ACCOUNT_ID', '')
    )
    
    data = tracker.generate_finops_dashboard_data()
    
    return CostSummary(
        total_cost_usd=data["current_month_costs"]["total_cost_usd"],
        by_service=data["current_month_costs"]["by_service"],
        token_costs=data["token_costs"],
        budget_status=data["budget_status"]
    )


@finops_router.get("/anomalies", response_model=List[CostAnomaly])
@require_role("admin")
async def get_cost_anomalies():
    """Get cost anomalies (admin only)."""
    tracker = FinOpsTracker(
        project_id=config.PROJECT_ID,
        billing_account_id=getattr(config, 'BILLING_ACCOUNT_ID', '')
    )
    
    anomalies = tracker.detect_cost_anomalies()
    
    return [
        CostAnomaly(**anomaly)
        for anomaly in anomalies
    ]


@finops_router.get("/budget-status")
@require_role("admin")
async def get_budget_status():
    """Get budget status and alerts (admin only)."""
    tracker = FinOpsTracker(
        project_id=config.PROJECT_ID,
        billing_account_id=getattr(config, 'BILLING_ACCOUNT_ID', '')
    )
    
    return tracker.get_budget_status()


@finops_router.get("/token-usage")
@require_role("admin")
async def get_token_usage(days: int = 30):
    """Get token usage statistics (admin only)."""
    tracker = FinOpsTracker(
        project_id=config.PROJECT_ID,
        billing_account_id=getattr(config, 'BILLING_ACCOUNT_ID', '')
    )
    
    return tracker.get_token_costs(days=days)


@finops_router.get("/recommendations")
@require_role("admin")
async def get_cost_recommendations():
    """Get cost optimization recommendations (admin only)."""
    tracker = FinOpsTracker(
        project_id=config.PROJECT_ID,
        billing_account_id=getattr(config, 'BILLING_ACCOUNT_ID', '')
    )
    
    data = tracker.generate_finops_dashboard_data()
    return {"recommendations": data["recommendations"]}
