"""
Synthetic Monitoring - Week 4
Performs synthetic monitoring checks for reliability.
"""

import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Any
from google.cloud import firestore
from app.logging_config import get_logger

logger = get_logger(__name__)


class SyntheticMonitor:
    """
    Performs synthetic monitoring checks on application endpoints.
    """
    
    def __init__(self, base_url: str, firestore_client):
        """
        Initialize synthetic monitor.
        
        Args:
            base_url: Base URL of the application
            firestore_client: Firestore client instance
        """
        self.base_url = base_url.rstrip("/")
        self.db = firestore_client
        self.checks_collection = "synthetic_checks"
    
    async def check_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        expected_status: int = 200,
        timeout: int = 10,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Check a single endpoint.
        
        Args:
            endpoint: Endpoint path
            method: HTTP method
            expected_status: Expected status code
            timeout: Timeout in seconds
            headers: Request headers
            
        Returns:
            Check result
        """
        url = f"{self.base_url}{endpoint}"
        start_time = datetime.utcnow()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    headers=headers or {}
                ) as response:
                    end_time = datetime.utcnow()
                    latency_ms = (end_time - start_time).total_seconds() * 1000
                    
                    status_ok = response.status == expected_status
                    
                    return {
                        "endpoint": endpoint,
                        "url": url,
                        "method": method,
                        "status_code": response.status,
                        "expected_status": expected_status,
                        "latency_ms": latency_ms,
                        "success": status_ok,
                        "error": None if status_ok else f"Status {response.status} != {expected_status}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
        except asyncio.TimeoutError:
            return {
                "endpoint": endpoint,
                "url": url,
                "method": method,
                "status_code": 0,
                "expected_status": expected_status,
                "latency_ms": timeout * 1000,
                "success": False,
                "error": f"Timeout after {timeout}s",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "endpoint": endpoint,
                "url": url,
                "method": method,
                "status_code": 0,
                "expected_status": expected_status,
                "latency_ms": 0,
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def run_health_checks(
        self,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run comprehensive health checks on all critical endpoints.
        
        Args:
            auth_token: Optional auth token for authenticated endpoints
            
        Returns:
            Aggregated health check results
        """
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        # Define critical endpoints to check
        endpoints = [
            {"path": "/health", "method": "GET", "expected": 200, "auth": False},
            {"path": "/api/config", "method": "GET", "expected": 200, "auth": False},
            {"path": "/api/documents", "method": "GET", "expected": 200, "auth": True},
            {"path": "/api/chat", "method": "GET", "expected": 200, "auth": True},
            {"path": "/compliance/reports", "method": "GET", "expected": 200, "auth": True},
        ]
        
        tasks = []
        for endpoint_config in endpoints:
            req_headers = headers if endpoint_config.get("auth") else {}
            tasks.append(
                self.check_endpoint(
                    endpoint_config["path"],
                    endpoint_config["method"],
                    endpoint_config["expected"],
                    headers=req_headers
                )
            )
        
        results = await asyncio.gather(*tasks)
        
        # Calculate summary
        total_checks = len(results)
        successful_checks = sum(1 for r in results if r["success"])
        failed_checks = total_checks - successful_checks
        avg_latency = sum(r["latency_ms"] for r in results) / total_checks if total_checks > 0 else 0
        
        health_status = "healthy" if failed_checks == 0 else "degraded" if failed_checks < total_checks / 2 else "unhealthy"
        
        summary = {
            "status": health_status,
            "total_checks": total_checks,
            "successful": successful_checks,
            "failed": failed_checks,
            "success_rate": (successful_checks / total_checks * 100) if total_checks > 0 else 0,
            "avg_latency_ms": avg_latency,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store results
        self._store_check_results(summary, results)
        
        return {
            "summary": summary,
            "details": results
        }
    
    def _store_check_results(self, summary: Dict[str, Any], details: List[Dict[str, Any]]):
        """Store check results in Firestore."""
        try:
            check_doc = {
                "summary": summary,
                "details": details,
                "timestamp": datetime.utcnow()
            }
            
            self.db.collection(self.checks_collection).add(check_doc)
            
        except Exception as e:
            logger.error(f"Error storing check results: {e}")
    
    def get_recent_checks(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent synthetic check results.
        
        Args:
            hours: Hours to look back
            limit: Maximum number of results
            
        Returns:
            List of check results
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            checks = self.db.collection(self.checks_collection) \
                .where("timestamp", ">=", cutoff_time) \
                .order_by("timestamp", direction=firestore.Query.DESCENDING) \
                .limit(limit) \
                .stream()
            
            results = []
            for doc in checks:
                data = doc.to_dict()
                results.append(data)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting recent checks: {e}")
            return []
    
    def get_uptime_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Calculate uptime statistics.
        
        Args:
            hours: Hours to analyze
            
        Returns:
            Uptime statistics
        """
        try:
            checks = self.get_recent_checks(hours)
            
            if not checks:
                return {
                    "uptime_percent": 100.0,
                    "total_checks": 0,
                    "successful_checks": 0,
                    "failed_checks": 0,
                    "period_hours": hours
                }
            
            total_checks = len(checks)
            successful_checks = sum(1 for c in checks if c.get("summary", {}).get("status") == "healthy")
            failed_checks = total_checks - successful_checks
            
            uptime_percent = (successful_checks / total_checks * 100) if total_checks > 0 else 100.0
            
            # Calculate downtime incidents
            incidents = []
            current_incident = None
            
            for check in sorted(checks, key=lambda x: x.get("timestamp", datetime.min)):
                status = check.get("summary", {}).get("status")
                timestamp = check.get("timestamp")
                
                if status != "healthy":
                    if current_incident is None:
                        current_incident = {
                            "start": timestamp,
                            "end": timestamp,
                            "duration_minutes": 0
                        }
                    else:
                        current_incident["end"] = timestamp
                else:
                    if current_incident:
                        # Calculate duration
                        if isinstance(current_incident["start"], datetime):
                            duration = (current_incident["end"] - current_incident["start"]).total_seconds() / 60
                            current_incident["duration_minutes"] = duration
                        incidents.append(current_incident)
                        current_incident = None
            
            # Add ongoing incident
            if current_incident:
                incidents.append(current_incident)
            
            return {
                "uptime_percent": uptime_percent,
                "total_checks": total_checks,
                "successful_checks": successful_checks,
                "failed_checks": failed_checks,
                "incidents_count": len(incidents),
                "incidents": incidents,
                "period_hours": hours,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating uptime stats: {e}")
            return {"error": str(e)}
    
    async def run_continuous_monitoring(
        self,
        interval_seconds: int = 60,
        duration_minutes: Optional[int] = None
    ):
        """
        Run continuous monitoring for a specified duration.
        
        Args:
            interval_seconds: Interval between checks
            duration_minutes: Total duration (None for infinite)
        """
        start_time = datetime.utcnow()
        iterations = 0
        
        logger.info(f"Starting continuous monitoring (interval: {interval_seconds}s)")
        
        while True:
            try:
                # Run checks
                results = await self.run_health_checks()
                iterations += 1
                
                logger.info(f"Check #{iterations}: {results['summary']['status']} "
                           f"({results['summary']['successful']}/{results['summary']['total_checks']} successful)")
                
                # Check if duration exceeded
                if duration_minutes:
                    elapsed_minutes = (datetime.utcnow() - start_time).total_seconds() / 60
                    if elapsed_minutes >= duration_minutes:
                        logger.info(f"Monitoring completed after {iterations} iterations")
                        break
                
                # Wait for next interval
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in continuous monitoring: {e}")
                await asyncio.sleep(interval_seconds)


# _week4
