#!/usr/bin/env python3
"""
Monitor canary deployment metrics and auto-rollback on regression.
"""

import time
from google.cloud import monitoring_v3
import subprocess
import sys
from typing import Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CanaryMonitor:
    """Monitor canary deployment health and rollback if needed."""
    
    def __init__(
        self,
        project_id: str,
        cluster_name: str,
        region: str,
        error_rate_threshold: float = 0.05,  # 5%
        latency_threshold_ms: float = 2000  # 2s p95
    ):
        self.project_id = project_id
        self.cluster_name = cluster_name
        self.region = region
        self.error_rate_threshold = error_rate_threshold
        self.latency_threshold_ms = latency_threshold_ms
        
        self.monitoring_client = monitoring_v3.MetricServiceClient()
    
    def check_canary_health(self) -> Dict[str, Any]:
        """
        Check canary deployment metrics.
        
        Returns:
            Health status and metrics
        """
        # Query Cloud Monitoring for canary metrics
        project_name = f"projects/{self.project_id}"
        
        # Error rate query
        error_rate = self._query_error_rate("canary")
        stable_error_rate = self._query_error_rate("stable")
        
        # Latency query
        canary_latency = self._query_latency("canary")
        stable_latency = self._query_latency("stable")
        
        # Compare
        health_status = {
            "canary_error_rate": error_rate,
            "stable_error_rate": stable_error_rate,
            "canary_latency_p95": canary_latency,
            "stable_latency_p95": stable_latency,
            "error_rate_regression": error_rate > stable_error_rate * 1.5,
            "latency_regression": canary_latency > stable_latency * 1.2,
            "should_rollback": False
        }
        
        # Determine if rollback is needed
        if (error_rate > self.error_rate_threshold or
            health_status["error_rate_regression"] or
            health_status["latency_regression"]):
            health_status["should_rollback"] = True
        
        return health_status
    
    def _query_error_rate(self, version: str) -> float:
        """Query error rate from Cloud Monitoring."""
        # Mock implementation - replace with actual query
        return 0.02 if version == "canary" else 0.01
    
    def _query_latency(self, version: str) -> float:
        """Query p95 latency from Cloud Monitoring."""
        # Mock implementation - replace with actual query
        return 1500.0 if version == "canary" else 1200.0
    
    def rollback_canary(self):
        """Rollback canary deployment."""
        logger.warning("Rolling back canary deployment")
        
        try:
            # Scale canary to 0
            result = subprocess.run(
                ["kubectl", "scale", "deployment", "rag-backend-canary", "--replicas=0"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("Canary rolled back successfully")
            else:
                logger.error(f"Rollback failed: {result.stderr}")
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
    
    def promote_canary(self):
        """Promote canary to stable (full rollout)."""
        logger.info("Promoting canary to stable")
        
        try:
            # Update stable deployment with canary image
            result = subprocess.run(
                ["kubectl", "set", "image", "deployment/rag-backend",
                 "backend=gcr.io/btoproject-486405/rag-backend:canary"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("Canary promoted to stable")
                
                # Scale canary to 0
                subprocess.run(
                    ["kubectl", "scale", "deployment", "rag-backend-canary", "--replicas=0"],
                    capture_output=True,
                    text=True
                )
                
                logger.info("Canary deployment scaled down")
            else:
                logger.error(f"Promotion failed: {result.stderr}")
        except Exception as e:
            logger.error(f"Error during promotion: {e}")
    
    def run_monitoring_loop(self, interval_seconds: int = 60, max_iterations: int = 60):
        """Continuously monitor canary and auto-rollback if needed."""
        logger.info(f"Starting canary monitoring (interval: {interval_seconds}s)")
        
        for i in range(max_iterations):
            health = self.check_canary_health()
            
            logger.info(
                f"Canary health check #{i+1}: "
                f"error_rate={health['canary_error_rate']:.4f}, "
                f"latency_p95={health['canary_latency_p95']:.2f}ms"
            )
            
            if health["should_rollback"]:
                logger.error("Canary health degraded - initiating rollback")
                self.rollback_canary()
                return False
            
            time.sleep(interval_seconds)
        
        logger.info("Monitoring period completed - canary is healthy")
        return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor canary deployment")
    parser.add_argument("--project-id", default="btoproject-486405", help="GCP Project ID")
    parser.add_argument("--cluster", default="rag-chatbot-cluster", help="GKE cluster name")
    parser.add_argument("--region", default="us-central1", help="GCP region")
    parser.add_argument("--interval", type=int, default=60, help="Monitoring interval in seconds")
    parser.add_argument("--iterations", type=int, default=60, help="Number of monitoring iterations")
    
    args = parser.parse_args()
    
    monitor = CanaryMonitor(
        project_id=args.project_id,
        cluster_name=args.cluster,
        region=args.region
    )
    
    success = monitor.run_monitoring_loop(
        interval_seconds=args.interval,
        max_iterations=args.iterations
    )
    
    if success:
        print("\n✓ Canary is healthy - ready for promotion")
        sys.exit(0)
    else:
        print("\n✗ Canary rolled back due to health issues")
        sys.exit(1)


if __name__ == "__main__":
    main()
