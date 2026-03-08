"""
Variant Manager - Week 4
Manages prompt, model, and embedding variants for A/B testing.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import json
from app.logging_config import get_logger

logger = get_logger(__name__)


class VariantType(str, Enum):
    """Types of variants."""
    PROMPT = "prompt"
    MODEL = "model"
    EMBEDDING = "embedding"


class VariantManager:
    """
    Manages variants for A/B testing and canary releases.
    Stores variant configurations and tracks performance.
    """
    
    def __init__(self, firestore_client):
        """
        Initialize variant manager.
        
        Args:
            firestore_client: Firestore client instance
        """
        self.db = firestore_client
        self.variants_collection = "experiment_variants"
    
    def create_variant(
        self,
        variant_name: str,
        variant_type: VariantType,
        config: Dict[str, Any],
        traffic_percentage: float = 0.0,
        description: Optional[str] = None
    ) -> str:
        """
        Create a new variant.
        
        Args:
            variant_name: Unique variant name
            variant_type: Type of variant
            config: Variant configuration
            traffic_percentage: Initial traffic allocation (0-100)
            description: Variant description
            
        Returns:
            Variant ID
        """
        try:
            variant_doc = {
                "variant_id": variant_name,
                "variant_type": variant_type.value,
                "config": config,
                "traffic_percentage": traffic_percentage,
                "status": "inactive",
                "description": description or "",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "metrics": {
                    "requests": 0,
                    "errors": 0,
                    "avg_latency_ms": 0.0,
                    "avg_cost": 0.0
                }
            }
            
            self.db.collection(self.variants_collection).document(variant_name).set(variant_doc)
            
            logger.info(f"Created variant: {variant_name} ({variant_type.value})")
            return variant_name
            
        except Exception as e:
            logger.error(f"Error creating variant: {e}")
            raise
    
    def get_variant(self, variant_name: str) -> Optional[Dict[str, Any]]:
        """
        Get variant configuration.
        
        Args:
            variant_name: Variant name
            
        Returns:
            Variant data or None
        """
        try:
            doc = self.db.collection(self.variants_collection).document(variant_name).get()
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"Error getting variant: {e}")
            return None
    
    def list_variants(
        self,
        variant_type: Optional[VariantType] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List variants with optional filters.
        
        Args:
            variant_type: Filter by variant type
            status: Filter by status (active, inactive)
            
        Returns:
            List of variants
        """
        try:
            query = self.db.collection(self.variants_collection)
            
            if variant_type:
                query = query.where("variant_type", "==", variant_type.value)
            if status:
                query = query.where("status", "==", status)
            
            variants = []
            for doc in query.stream():
                variant_data = doc.to_dict()
                variant_data["variant_id"] = doc.id
                variants.append(variant_data)
            
            logger.info(f"Listed {len(variants)} variants")
            return variants
            
        except Exception as e:
            logger.error(f"Error listing variants: {e}")
            return []
    
    def update_variant_traffic(self, variant_name: str, traffic_percentage: float) -> bool:
        """
        Update traffic allocation for a variant.
        
        Args:
            variant_name: Variant name
            traffic_percentage: New traffic percentage (0-100)
            
        Returns:
            Success status
        """
        try:
            if not 0 <= traffic_percentage <= 100:
                raise ValueError("Traffic percentage must be between 0 and 100")
            
            self.db.collection(self.variants_collection).document(variant_name).update({
                "traffic_percentage": traffic_percentage,
                "updated_at": datetime.utcnow()
            })
            
            logger.info(f"Updated variant {variant_name} traffic to {traffic_percentage}%")
            return True
            
        except Exception as e:
            logger.error(f"Error updating variant traffic: {e}")
            return False
    
    def activate_variant(self, variant_name: str) -> bool:
        """
        Activate a variant for testing.
        
        Args:
            variant_name: Variant name
            
        Returns:
            Success status
        """
        try:
            self.db.collection(self.variants_collection).document(variant_name).update({
                "status": "active",
                "activated_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            
            logger.info(f"Activated variant: {variant_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error activating variant: {e}")
            return False
    
    def deactivate_variant(self, variant_name: str) -> bool:
        """
        Deactivate a variant.
        
        Args:
            variant_name: Variant name
            
        Returns:
            Success status
        """
        try:
            self.db.collection(self.variants_collection).document(variant_name).update({
                "status": "inactive",
                "deactivated_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            
            logger.info(f"Deactivated variant: {variant_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deactivating variant: {e}")
            return False
    
    def update_variant_metrics(
        self,
        variant_name: str,
        requests: int = 0,
        errors: int = 0,
        latency_ms: Optional[float] = None,
        cost: Optional[float] = None
    ):
        """
        Update metrics for a variant.
        
        Args:
            variant_name: Variant name
            requests: Number of requests
            errors: Number of errors
            latency_ms: Latency in milliseconds
            cost: Cost per request
        """
        try:
            variant = self.get_variant(variant_name)
            if not variant:
                logger.warning(f"Variant {variant_name} not found")
                return
            
            current_metrics = variant.get("metrics", {})
            total_requests = current_metrics.get("requests", 0) + requests
            total_errors = current_metrics.get("errors", 0) + errors
            
            # Calculate running averages
            if latency_ms is not None and total_requests > 0:
                current_avg = current_metrics.get("avg_latency_ms", 0.0)
                new_avg = ((current_avg * (total_requests - requests)) + (latency_ms * requests)) / total_requests
            else:
                new_avg = current_metrics.get("avg_latency_ms", 0.0)
            
            if cost is not None and total_requests > 0:
                current_avg_cost = current_metrics.get("avg_cost", 0.0)
                new_avg_cost = ((current_avg_cost * (total_requests - requests)) + (cost * requests)) / total_requests
            else:
                new_avg_cost = current_metrics.get("avg_cost", 0.0)
            
            updated_metrics = {
                "requests": total_requests,
                "errors": total_errors,
                "error_rate": (total_errors / total_requests * 100) if total_requests > 0 else 0.0,
                "avg_latency_ms": new_avg,
                "avg_cost": new_avg_cost
            }
            
            self.db.collection(self.variants_collection).document(variant_name).update({
                "metrics": updated_metrics,
                "updated_at": datetime.utcnow()
            })
            
            logger.info(f"Updated metrics for variant {variant_name}")
            
        except Exception as e:
            logger.error(f"Error updating variant metrics: {e}")
    
    def get_active_variants(self, variant_type: Optional[VariantType] = None) -> List[Dict[str, Any]]:
        """
        Get all active variants.
        
        Args:
            variant_type: Filter by variant type
            
        Returns:
            List of active variants
        """
        return self.list_variants(variant_type=variant_type, status="active")
    
    def get_traffic_distribution(self) -> Dict[str, float]:
        """
        Get current traffic distribution across all active variants.
        
        Returns:
            Variant name to traffic percentage mapping
        """
        try:
            active_variants = self.get_active_variants()
            distribution = {}
            
            for variant in active_variants:
                distribution[variant["variant_id"]] = variant.get("traffic_percentage", 0.0)
            
            # Calculate baseline (100 - sum of variant traffic)
            total_variant_traffic = sum(distribution.values())
            distribution["baseline"] = max(0, 100 - total_variant_traffic)
            
            return distribution
            
        except Exception as e:
            logger.error(f"Error getting traffic distribution: {e}")
            return {"baseline": 100.0}


# Predefined variants for common scenarios
PROMPT_VARIANTS = {
    "concise": {
        "system_instruction": "You are a helpful assistant. Provide concise, direct answers.",
        "temperature": 0.3
    },
    "detailed": {
        "system_instruction": "You are a helpful assistant. Provide detailed, comprehensive answers with examples.",
        "temperature": 0.7
    },
    "technical": {
        "system_instruction": "You are a technical expert. Provide precise, technical answers with code examples when relevant.",
        "temperature": 0.5
    }
}

MODEL_VARIANTS = {
    "gemini-pro": {
        "model_name": "gemini-1.5-pro-002",
        "max_tokens": 8192,
        "temperature": 0.5
    },
    "gemini-flash": {
        "model_name": "gemini-1.5-flash-002",
        "max_tokens": 8192,
        "temperature": 0.5
    }
}

EMBEDDING_VARIANTS = {
    "gecko-003": {
        "model_name": "textembedding-gecko@003",
        "dimensions": 768
    },
    "gecko-multilingual": {
        "model_name": "textembedding-gecko-multilingual@001",
        "dimensions": 768
    }
}


# _week4
