"""
Experiment API Routes - Week 4
FastAPI routes for managing experiments, variants, and A/B testing.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

from app.config import PROJECT_ID, REGION
from app.logging_config import get_logger
from google.cloud import firestore

from app.experiments.experiment_tracker_week4 import ExperimentTracker
from app.experiments.model_registry_week4 import ModelRegistry
from app.experiments.variant_manager_week4 import VariantManager, VariantType, PROMPT_VARIANTS, MODEL_VARIANTS
from app.experiments.ab_testing_week4 import ABTestingFramework
from app.experiments.feature_flags_week4 import FeatureFlagManager, FeatureFlagStatus

logger = get_logger(__name__)
router = APIRouter(prefix="/experiments", tags=["experiments_week4"])

# Initialize clients
db = firestore.Client(project=PROJECT_ID)
experiment_tracker = ExperimentTracker(PROJECT_ID, REGION)
model_registry = ModelRegistry(PROJECT_ID, REGION)
variant_manager = VariantManager(db)
ab_testing = ABTestingFramework(variant_manager)
feature_flags = FeatureFlagManager(db)


# Pydantic models
class CreateVariantRequest(BaseModel):
    variant_name: str
    variant_type: VariantType
    config: Dict[str, Any]
    traffic_percentage: float = Field(0.0, ge=0, le=100)
    description: Optional[str] = None


class UpdateTrafficRequest(BaseModel):
    traffic_percentage: float = Field(..., ge=0, le=100)


class RecordMetricsRequest(BaseModel):
    variant_name: str
    success: bool
    latency_ms: float
    cost: float = 0.0


class GradualRolloutRequest(BaseModel):
    target_percentage: float = Field(..., ge=0, le=100)
    increment: float = Field(10.0, ge=1, le=50)
    success_threshold: float = Field(95.0, ge=0, le=100)


class CreateFeatureFlagRequest(BaseModel):
    flag_name: str
    description: str
    status: FeatureFlagStatus = FeatureFlagStatus.DISABLED
    rollout_percentage: float = Field(0.0, ge=0, le=100)
    enabled_users: Optional[List[str]] = None


# Variant management endpoints
@router.post("/variants")
async def create_variant(
    request: CreateVariantRequest
):
    """Create a new variant for A/B testing (admin only)."""
    try:
        variant_id = variant_manager.create_variant(
            variant_name=request.variant_name,
            variant_type=request.variant_type,
            config=request.config,
            traffic_percentage=request.traffic_percentage,
            description=request.description
        )
        
        return {
            "variant_id": variant_id,
            "status": "created",
            "message": f"Variant {variant_id} created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating variant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/variants")
async def list_variants(
    variant_type: Optional[VariantType] = None,
    status: Optional[str] = None
):
    """List all variants with optional filters."""
    try:
        variants = variant_manager.list_variants(variant_type, status)
        return {
            "variants": variants,
            "count": len(variants)
        }
    except Exception as e:
        logger.error(f"Error listing variants: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/variants/{variant_name}")
async def get_variant(
    variant_name: str
):
    """Get details of a specific variant."""
    variant = variant_manager.get_variant(variant_name)
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    return variant


@router.put("/variants/{variant_name}/traffic")
async def update_variant_traffic(
    variant_name: str,
    request: UpdateTrafficRequest = None,
    weight: float = Query(None, ge=0, le=100, description="Traffic weight (alternative to request body)")
):
    """Update traffic allocation for a variant (admin only)."""
    try:
        # Accept weight from either request body or query parameter
        traffic_percentage = weight if weight is not None else (request.traffic_percentage if request else None)
        
        if traffic_percentage is None:
            raise HTTPException(status_code=400, detail="Must provide either 'weight' query parameter or request body")
        
        success = variant_manager.update_variant_traffic(
            variant_name,
            traffic_percentage
        )
        
        if success:
            return {
                "status": "updated",
                "variant_name": variant_name,
                "variant_id": variant_name,
                "traffic_percentage": traffic_percentage,
                "weight": traffic_percentage
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update traffic")
    except Exception as e:
        logger.error(f"Error updating traffic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/variants/{variant_name}/activate")
async def activate_variant(
    variant_name: str
):
    """Activate a variant (admin only). variant_name can also be variant_id."""
    try:
        # variant_name from URL path can be either name or ID
        success = variant_manager.activate_variant(variant_name)
        if success:
            return {"status": "activated", "variant_name": variant_name, "variant_id": variant_name}
        else:
            raise HTTPException(status_code=500, detail="Failed to activate variant")
    except Exception as e:
        logger.error(f"Error activating variant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/variants/{variant_name}/deactivate")
async def deactivate_variant(
    variant_name: str
):
    """Deactivate a variant (admin only). variant_name can also be variant_id."""
    try:
        # variant_name from URL path can be either name or ID
        success = variant_manager.deactivate_variant(variant_name)
        if success:
            return {"status": "deactivated", "variant_name": variant_name, "variant_id": variant_name}
        else:
            raise HTTPException(status_code=500, detail="Failed to deactivate variant")
    except Exception as e:
        logger.error(f"Error deactivating variant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# A/B testing endpoints
@router.post("/select-variant")
async def select_variant(
    variant_type: VariantType
):
    """Select a variant for the current user based on A/B testing rules."""
    try:
        user_id = user.get("email", "anonymous")
        variant_name, config = ab_testing.select_variant(user_id, variant_type, sticky=True)
        
        return {
            "variant_name": variant_name,
            "variant_type": variant_type.value,
            "config": config,
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Error selecting variant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record-interaction")
async def record_interaction(
    request: RecordMetricsRequest
):
    """Record an interaction with a variant for metrics tracking."""
    try:
        ab_testing.record_interaction(
            variant_name=request.variant_name,
            success=request.success,
            latency_ms=request.latency_ms,
            cost=request.cost
        )
        
        return {"status": "recorded"}
    except Exception as e:
        logger.error(f"Error recording interaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results")
async def get_experiment_results(
    days: int = Query(7, ge=1, le=90),
    variant_names: Optional[str] = Query(None, description="Comma-separated list of variants")
):
    """Get A/B test results comparing variants (admin only)."""
    try:
        # Get all active variants if variant_names not specified
        if variant_names:
            variants = [v.strip() for v in variant_names.split(",")]
        else:
            # Get all active variants
            all_variants = variant_manager.list_variants()
            variants = [v["name"] for v in all_variants if v.get("is_active", True)]
        
        results = ab_testing.get_experiment_results(variants)
        return {"results": results if isinstance(results, list) else [results]}
    except Exception as e:
        logger.error(f"Error getting experiment results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/variants/{variant_name}/rollout")
async def gradual_rollout(
    variant_name: str,
    request: GradualRolloutRequest
):
    """Perform gradual rollout of a variant (admin only)."""
    try:
        result = ab_testing.gradual_rollout(
            variant_name=variant_name,
            target_percentage=request.target_percentage,
            increment=request.increment,
            success_threshold=request.success_threshold
        )
        return result
    except Exception as e:
        logger.error(f"Error in gradual rollout: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/variants/{variant_name}/check-rollback")
async def check_auto_rollback(
    variant_name: str,
    error_rate_threshold: float = 5.0,
    min_requests: int = 100
):
    """Check if variant should be rolled back based on performance (admin only)."""
    try:
        result = ab_testing.auto_rollback(
            variant_name=variant_name,
            error_rate_threshold=error_rate_threshold,
            min_requests=min_requests
        )
        return result
    except Exception as e:
        logger.error(f"Error checking rollback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Feature flags endpoints
@router.post("/feature-flags")
async def create_feature_flag(
    request: CreateFeatureFlagRequest
):
    """Create a new feature flag (admin only)."""
    try:
        flag_id = feature_flags.create_flag(
            flag_name=request.flag_name,
            description=request.description,
            status=request.status,
            rollout_percentage=request.rollout_percentage,
            enabled_users=request.enabled_users
        )
        
        return {
            "flag_id": flag_id,
            "status": "created"
        }
    except Exception as e:
        logger.error(f"Error creating feature flag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feature-flags")
async def list_feature_flags(
    status: Optional[FeatureFlagStatus] = None
):
    """List all feature flags."""
    try:
        flags = feature_flags.list_flags(status)
        return {
            "flags": flags,
            "count": len(flags)
        }
    except Exception as e:
        logger.error(f"Error listing feature flags: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feature-flags/{flag_name}/check")
async def check_feature_flag(
    flag_name: str
):
    """Check if a feature flag is enabled for current user."""
    try:
        user_id = user.get("email")
        enabled = feature_flags.is_enabled(flag_name, user_id)
        
        return {
            "flag_name": flag_name,
            "enabled": enabled,
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Error checking feature flag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feature-flags/{flag_name}/enable")
async def enable_feature_flag(
    flag_name: str
):
    """Enable a feature flag globally (admin only). flag_name can also be flag_id."""
    try:
        # flag_name from URL path can be either name or ID
        success = feature_flags.enable_flag(flag_name)
        if success:
            return {"status": "enabled", "flag_name": flag_name, "flag_id": flag_name}
        else:
            raise HTTPException(status_code=500, detail="Failed to enable flag")
    except Exception as e:
        logger.error(f"Error enabling feature flag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feature-flags/{flag_name}/disable")
async def disable_feature_flag(
    flag_name: str
):
    """Disable a feature flag globally (admin only). flag_name can also be flag_id."""
    try:
        # flag_name from URL path can be either name or ID
        success = feature_flags.disable_flag(flag_name)
        if success:
            return {"status": "disabled", "flag_name": flag_name, "flag_id": flag_name}
        else:
            raise HTTPException(status_code=500, detail="Failed to disable flag")
    except Exception as e:
        logger.error(f"Error disabling feature flag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traffic-distribution")
async def get_traffic_distribution():
    """Get current traffic distribution across all active variants."""
    try:
        distribution = variant_manager.get_traffic_distribution()
        return {
            "distribution": distribution,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting traffic distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predefined-variants")
async def get_predefined_variants():
    """Get predefined variant configurations (admin only)."""
    return {
        "prompt_variants": PROMPT_VARIANTS,
        "model_variants": MODEL_VARIANTS
    }


# _week4
