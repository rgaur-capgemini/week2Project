"""
A/B Testing Framework - Week 4
Manages A/B testing for prompt, model, and embedding variants.
"""

import random
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from app.logging_config import get_logger
from app.experiments.variant_manager_week4 import VariantManager, VariantType

logger = get_logger(__name__)


class ABTestingFramework:
    """
    A/B testing framework with traffic splitting and statistical analysis.
    """
    
    def __init__(self, variant_manager: VariantManager):
        """
        Initialize A/B testing framework.
        
        Args:
            variant_manager: VariantManager instance
        """
        self.variant_manager = variant_manager
    
    def select_variant(
        self,
        user_id: str,
        variant_type: VariantType,
        sticky: bool = True
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Select a variant for a user based on traffic distribution.
        
        Args:
            user_id: User identifier for consistent assignment
            variant_type: Type of variant to select
            sticky: If True, user gets same variant consistently
            
        Returns:
            Tuple of (variant_name, variant_config)
        """
        try:
            # Get active variants of the specified type
            active_variants = self.variant_manager.get_active_variants(variant_type)
            
            if not active_variants:
                logger.info(f"No active {variant_type.value} variants, using baseline")
                return ("baseline", {})
            
            # Get traffic distribution
            traffic_dist = {}
            for variant in active_variants:
                traffic_dist[variant["variant_id"]] = variant.get("traffic_percentage", 0.0)
            
            # Calculate baseline traffic
            total_variant_traffic = sum(traffic_dist.values())
            baseline_traffic = max(0, 100 - total_variant_traffic)
            traffic_dist["baseline"] = baseline_traffic
            
            # Select variant using consistent hashing (sticky) or random
            if sticky:
                variant_name = self._consistent_hash_selection(user_id, traffic_dist)
            else:
                variant_name = self._random_selection(traffic_dist)
            
            # Get variant config
            if variant_name == "baseline":
                return ("baseline", {})
            
            variant = self.variant_manager.get_variant(variant_name)
            if variant:
                logger.info(f"Selected variant {variant_name} for user {user_id}")
                return (variant_name, variant.get("config", {}))
            else:
                logger.warning(f"Variant {variant_name} not found, using baseline")
                return ("baseline", {})
                
        except Exception as e:
            logger.error(f"Error selecting variant: {e}")
            return ("baseline", {})
    
    def _consistent_hash_selection(self, user_id: str, traffic_dist: Dict[str, float]) -> str:
        """
        Select variant using consistent hashing for sticky assignment.
        
        Args:
            user_id: User identifier
            traffic_dist: Variant to traffic percentage mapping
            
        Returns:
            Selected variant name
        """
        # Create hash of user_id
        hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        percentage = (hash_value % 10000) / 100.0  # 0-100 with 2 decimal precision
        
        # Select variant based on cumulative distribution
        cumulative = 0.0
        for variant_name, traffic in sorted(traffic_dist.items()):
            cumulative += traffic
            if percentage < cumulative:
                return variant_name
        
        # Fallback to baseline
        return "baseline"
    
    def _random_selection(self, traffic_dist: Dict[str, float]) -> str:
        """
        Select variant randomly based on traffic distribution.
        
        Args:
            traffic_dist: Variant to traffic percentage mapping
            
        Returns:
            Selected variant name
        """
        rand_value = random.uniform(0, 100)
        
        cumulative = 0.0
        for variant_name, traffic in sorted(traffic_dist.items()):
            cumulative += traffic
            if rand_value < cumulative:
                return variant_name
        
        return "baseline"
    
    def record_interaction(
        self,
        variant_name: str,
        success: bool,
        latency_ms: float,
        cost: float = 0.0
    ):
        """
        Record an interaction with a variant.
        
        Args:
            variant_name: Variant that was used
            success: Whether interaction was successful
            latency_ms: Latency in milliseconds
            cost: Cost of the interaction
        """
        if variant_name == "baseline":
            return  # Don't track baseline separately
        
        try:
            self.variant_manager.update_variant_metrics(
                variant_name=variant_name,
                requests=1,
                errors=0 if success else 1,
                latency_ms=latency_ms,
                cost=cost
            )
            
        except Exception as e:
            logger.error(f"Error recording interaction: {e}")
    
    def get_experiment_results(self, variant_names: List[str]) -> Dict[str, Any]:
        """
        Get A/B test results comparing variants.
        
        Args:
            variant_names: List of variant names to compare
            
        Returns:
            Comparison results
        """
        try:
            results = []
            
            for variant_name in variant_names:
                variant = self.variant_manager.get_variant(variant_name)
                if variant:
                    metrics = variant.get("metrics", {})
                    results.append({
                        "variant_name": variant_name,
                        "variant_type": variant.get("variant_type"),
                        "traffic_percentage": variant.get("traffic_percentage", 0),
                        "status": variant.get("status"),
                        "metrics": {
                            "total_requests": metrics.get("requests", 0),
                            "error_rate": metrics.get("error_rate", 0.0),
                            "avg_latency_ms": metrics.get("avg_latency_ms", 0.0),
                            "avg_cost": metrics.get("avg_cost", 0.0)
                        }
                    })
            
            # Calculate winner
            winner = None
            if results:
                # Simple scoring: lower error rate + lower latency + lower cost
                for result in results:
                    metrics = result["metrics"]
                    score = (
                        (100 - metrics["error_rate"]) * 0.4 +  # 40% weight on reliability
                        (1000 / max(metrics["avg_latency_ms"], 1)) * 0.3 +  # 30% weight on speed
                        (1 / max(metrics["avg_cost"], 0.001)) * 0.3  # 30% weight on cost
                    )
                    result["score"] = score
                
                winner = max(results, key=lambda x: x.get("score", 0))
            
            return {
                "results": results,
                "winner": winner["variant_name"] if winner else None,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting experiment results: {e}")
            return {"results": [], "winner": None}
    
    def gradual_rollout(
        self,
        variant_name: str,
        target_percentage: float,
        increment: float = 10.0,
        success_threshold: float = 95.0
    ) -> Dict[str, Any]:
        """
        Gradually increase traffic to a variant (canary rollout).
        
        Args:
            variant_name: Variant to roll out
            target_percentage: Target traffic percentage
            increment: Traffic increment per step
            success_threshold: Minimum success rate to continue (%)
            
        Returns:
            Rollout status
        """
        try:
            variant = self.variant_manager.get_variant(variant_name)
            if not variant:
                return {"status": "error", "message": "Variant not found"}
            
            current_traffic = variant.get("traffic_percentage", 0.0)
            metrics = variant.get("metrics", {})
            error_rate = metrics.get("error_rate", 0.0)
            success_rate = 100 - error_rate
            
            # Check if success rate meets threshold
            if success_rate < success_threshold:
                return {
                    "status": "paused",
                    "message": f"Success rate {success_rate:.2f}% below threshold {success_threshold}%",
                    "current_traffic": current_traffic,
                    "success_rate": success_rate
                }
            
            # Calculate new traffic
            new_traffic = min(current_traffic + increment, target_percentage)
            
            # Update traffic
            self.variant_manager.update_variant_traffic(variant_name, new_traffic)
            
            if new_traffic >= target_percentage:
                status = "completed"
                message = f"Rollout completed at {new_traffic}%"
            else:
                status = "in_progress"
                message = f"Rolled out to {new_traffic}% (target: {target_percentage}%)"
            
            return {
                "status": status,
                "message": message,
                "current_traffic": new_traffic,
                "target_traffic": target_percentage,
                "success_rate": success_rate
            }
            
        except Exception as e:
            logger.error(f"Error in gradual rollout: {e}")
            return {"status": "error", "message": str(e)}
    
    def auto_rollback(
        self,
        variant_name: str,
        error_rate_threshold: float = 5.0,
        min_requests: int = 100
    ) -> Dict[str, Any]:
        """
        Automatically rollback a variant if it's performing poorly.
        
        Args:
            variant_name: Variant to check
            error_rate_threshold: Maximum acceptable error rate (%)
            min_requests: Minimum requests before checking
            
        Returns:
            Rollback status
        """
        try:
            variant = self.variant_manager.get_variant(variant_name)
            if not variant:
                return {"status": "error", "message": "Variant not found"}
            
            metrics = variant.get("metrics", {})
            total_requests = metrics.get("requests", 0)
            error_rate = metrics.get("error_rate", 0.0)
            
            # Check if we have enough data
            if total_requests < min_requests:
                return {
                    "status": "insufficient_data",
                    "message": f"Only {total_requests} requests, need {min_requests}",
                    "rollback": False
                }
            
            # Check if error rate exceeds threshold
            if error_rate > error_rate_threshold:
                # Perform rollback
                self.variant_manager.update_variant_traffic(variant_name, 0.0)
                self.variant_manager.deactivate_variant(variant_name)
                
                return {
                    "status": "rolled_back",
                    "message": f"Error rate {error_rate:.2f}% exceeded threshold {error_rate_threshold}%",
                    "rollback": True,
                    "error_rate": error_rate,
                    "total_requests": total_requests
                }
            else:
                return {
                    "status": "healthy",
                    "message": f"Error rate {error_rate:.2f}% within threshold",
                    "rollback": False,
                    "error_rate": error_rate,
                    "total_requests": total_requests
                }
            
        except Exception as e:
            logger.error(f"Error in auto rollback: {e}")
            return {"status": "error", "message": str(e)}


# _week4
