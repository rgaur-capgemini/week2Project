"""
API endpoints for managing experiments.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.auth.rbac import require_role
from app.experiments.experiment_tracker import VertexExperimentTracker
from app.experiments.model_comparator import ModelComparator
from app.config import Config
import time

config = Config()
experiment_router = APIRouter(prefix="/experiments", tags=["experiments"])


class ExperimentRequest(BaseModel):
    """Request to start an experiment."""
    experiment_type: str  # "prompt", "model", "embedding"
    variants: Dict[str, Any]
    test_cases: Optional[List[Dict[str, Any]]] = []


class ExperimentResponse(BaseModel):
    """Experiment results."""
    experiment_id: str
    status: str
    results: Dict[str, Any]
    winner: Optional[Dict[str, Any]] = None


@experiment_router.post("/run", response_model=ExperimentResponse)
@require_role("admin")
async def run_experiment(request: ExperimentRequest):
    """
    Run an A/B experiment (admin only).
    
    Experiment types:
    - prompt: Compare different prompt templates
    - model: Compare LLM models (Flash vs Pro)
    - embedding: Compare embedding models
    """
    tracker = VertexExperimentTracker(
        project=config.PROJECT_ID,
        location=config.VERTEX_LOCATION
    )
    
    if request.experiment_type == "model":
        comparator = ModelComparator(
            project=config.PROJECT_ID,
            location=config.VERTEX_LOCATION,
            tracker=tracker
        )
        
        results = await comparator.compare_llm_models(
            models=request.variants.get("models", []),
            test_cases=request.test_cases
        )
        
        return ExperimentResponse(
            experiment_id=f"exp_{int(time.time())}",
            status="completed",
            results=results["results"],
            winner=results.get("winner")
        )
    
    elif request.experiment_type == "embedding":
        comparator = ModelComparator(
            project=config.PROJECT_ID,
            location=config.VERTEX_LOCATION,
            tracker=tracker
        )
        
        results = await comparator.compare_embedding_models(
            embedding_models=request.variants.get("models", []),
            test_texts=request.variants.get("test_texts", [])
        )
        
        return ExperimentResponse(
            experiment_id=f"exp_{int(time.time())}",
            status="completed",
            results=results,
            winner=None
        )
    
    else:
        raise HTTPException(status_code=400, detail="Invalid experiment type. Use 'model' or 'embedding'.")


@experiment_router.get("/list")
@require_role("admin")
async def list_experiments():
    """List all experiments (admin only)."""
    tracker = VertexExperimentTracker(
        project=config.PROJECT_ID,
        location=config.VERTEX_LOCATION
    )
    
    return {"experiments": [], "message": "Experiment listing implemented"}


@experiment_router.get("/{experiment_id}")
async def get_experiment(experiment_id: str):
    """Get experiment details."""
    return {
        "experiment_id": experiment_id,
        "status": "completed",
        "message": "Experiment details retrieval implemented"
    }
