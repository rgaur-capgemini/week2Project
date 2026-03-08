"""
Error Budget Tracker - Week 4
Tracks error budgets for SLO compliance.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from google.cloud import firestore
from app.logging_config import get_logger

logger = get_logger(__name__)


class ErrorBudgetTracker:
    """
    Tracks error budgets for service level objectives (SLOs).
    """
    
    def __init__(self, firestore_client):
        """
        Initialize error budget tracker.
        
        Args:
            firestore_client: Firestore client instance
        """
        self.db = firestore_client
        self.budgets_collection = "error_budgets"
        self.incidents_collection = "error_budget_incidents"
    
    def define_error_budget(
        self,
        service_name: str,
        slo_target: float,
        window_days: int = 30,
        description: Optional[str] = None
    ) -> str:
        """
        Define an error budget for a service.
        
        Args:
            service_name: Service name
            slo_target: SLO target percentage (e.g., 99.9 for 99.9%)
            window_days: Rolling window in days
            description: Budget description
            
        Returns:
            Budget ID
        """
        try:
            # Calculate allowed error percentage
            error_allowance = 100 - slo_target
            
            budget_doc = {
                "service_name": service_name,
                "slo_target": slo_target,
                "error_allowance_percent": error_allowance,
                "window_days": window_days,
                "description": description or "",
                "created_at": datetime.utcnow(),
                "status": "active"
            }
            
            doc_ref = self.db.collection(self.budgets_collection).document(service_name)
            doc_ref.set(budget_doc)
            
            logger.info(f"Defined error budget for {service_name}: {slo_target}% SLO")
            return service_name
            
        except Exception as e:
            logger.error(f"Error defining error budget: {e}")
            raise
    
    def calculate_error_budget_status(
        self,
        service_name: str,
        total_requests: int,
        failed_requests: int
    ) -> Dict[str, Any]:
        """
        Calculate current error budget status.
        
        Args:
            service_name: Service name
            total_requests: Total requests in window
            failed_requests: Failed requests in window
            
        Returns:
            Error budget status
        """
        try:
            # Get budget definition
            budget_doc = self.db.collection(self.budgets_collection).document(service_name).get()
            
            if not budget_doc.exists:
                return {
                    "status": "no_budget_defined",
                    "message": f"No error budget defined for {service_name}"
                }
            
            budget = budget_doc.to_dict()
            slo_target = budget.get("slo_target", 99.9)
            error_allowance_percent = budget.get("error_allowance_percent", 0.1)
            
            # Calculate actual error rate
            if total_requests == 0:
                actual_error_rate = 0.0
                availability = 100.0
            else:
                actual_error_rate = (failed_requests / total_requests) * 100
                availability = ((total_requests - failed_requests) / total_requests) * 100
            
            # Calculate error budget consumption
            error_budget_allowed = total_requests * (error_allowance_percent / 100)
            error_budget_consumed = failed_requests
            error_budget_remaining = max(0, error_budget_allowed - error_budget_consumed)
            
            # Calculate percentage remaining
            if error_budget_allowed > 0:
                budget_remaining_percent = (error_budget_remaining / error_budget_allowed) * 100
            else:
                budget_remaining_percent = 100.0
            
            # Determine status
            if budget_remaining_percent > 50:
                status = "healthy"
                severity = "none"
            elif budget_remaining_percent > 20:
                status = "warning"
                severity = "low"
            elif budget_remaining_percent > 0:
                status = "critical"
                severity = "high"
            else:
                status = "exhausted"
                severity = "critical"
            
            result = {
                "service_name": service_name,
                "slo_target": slo_target,
                "actual_availability": availability,
                "slo_met": availability >= slo_target,
                "error_rate_actual": actual_error_rate,
                "error_rate_allowed": error_allowance_percent,
                "error_budget": {
                    "allowed": error_budget_allowed,
                    "consumed": error_budget_consumed,
                    "remaining": error_budget_remaining,
                    "remaining_percent": budget_remaining_percent
                },
                "status": status,
                "severity": severity,
                "total_requests": total_requests,
                "failed_requests": failed_requests,
                "successful_requests": total_requests - failed_requests,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Record if critical or exhausted
            if status in ["critical", "exhausted"]:
                self._record_budget_incident(service_name, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating error budget: {e}")
            return {"status": "error", "message": str(e)}
    
    def _record_budget_incident(self, service_name: str, status: Dict[str, Any]):
        """Record an error budget incident."""
        try:
            incident_doc = {
                "service_name": service_name,
                "status": status.get("status"),
                "severity": status.get("severity"),
                "budget_remaining_percent": status.get("error_budget", {}).get("remaining_percent", 0),
                "availability": status.get("actual_availability", 0),
                "slo_target": status.get("slo_target", 0),
                "timestamp": datetime.utcnow()
            }
            
            self.db.collection(self.incidents_collection).add(incident_doc)
            
        except Exception as e:
            logger.error(f"Error recording budget incident: {e}")
    
    def get_budget_history(
        self,
        service_name: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get error budget history for a service.
        
        Args:
            service_name: Service name
            days: Number of days to look back
            
        Returns:
            List of budget snapshots
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            incidents = self.db.collection(self.incidents_collection) \
                .where("service_name", "==", service_name) \
                .where("timestamp", ">=", cutoff_time) \
                .order_by("timestamp", direction=firestore.Query.DESCENDING) \
                .stream()
            
            history = []
            for doc in incidents:
                data = doc.to_dict()
                history.append(data)
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting budget history: {e}")
            return []
    
    def get_all_budgets_status(self) -> List[Dict[str, Any]]:
        """
        Get status of all defined error budgets.
        
        Returns:
            List of budget statuses
        """
        try:
            budgets = self.db.collection(self.budgets_collection) \
                .where("status", "==", "active") \
                .stream()
            
            statuses = []
            for doc in budgets:
                budget = doc.to_dict()
                service_name = budget.get("service_name")
                
                # For demo purposes, return budget config
                # In production, would calculate from actual metrics
                statuses.append({
                    "service_name": service_name,
                    "slo_target": budget.get("slo_target"),
                    "window_days": budget.get("window_days"),
                    "status": "monitoring",
                    "description": budget.get("description")
                })
            
            return statuses
            
        except Exception as e:
            logger.error(f"Error getting all budgets: {e}")
            return []
    
    def project_budget_burn_rate(
        self,
        service_name: str,
        current_budget_remaining_percent: float,
        window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Project when error budget will be exhausted.
        
        Args:
            service_name: Service name
            current_budget_remaining_percent: Current budget remaining (%)
            window_days: Budget window in days
            
        Returns:
            Burn rate projection
        """
        try:
            # Get recent history
            history = self.get_budget_history(service_name, days=7)
            
            if len(history) < 2:
                return {
                    "service_name": service_name,
                    "message": "Insufficient data for projection",
                    "burn_rate": 0.0
                }
            
            # Calculate burn rate (percentage per day)
            oldest = history[-1]
            newest = history[0]
            
            time_diff_hours = (newest["timestamp"] - oldest["timestamp"]).total_seconds() / 3600
            time_diff_days = time_diff_hours / 24
            
            if time_diff_days > 0:
                budget_consumed = oldest.get("budget_remaining_percent", 100) - newest.get("budget_remaining_percent", 100)
                burn_rate_per_day = budget_consumed / time_diff_days
            else:
                burn_rate_per_day = 0.0
            
            # Project exhaustion time
            if burn_rate_per_day > 0:
                days_until_exhaustion = current_budget_remaining_percent / burn_rate_per_day
                exhaustion_date = datetime.utcnow() + timedelta(days=days_until_exhaustion)
            else:
                days_until_exhaustion = None
                exhaustion_date = None
            
            # Determine severity
            if days_until_exhaustion is None or days_until_exhaustion > window_days:
                severity = "none"
                alert = False
            elif days_until_exhaustion > 7:
                severity = "low"
                alert = False
            elif days_until_exhaustion > 3:
                severity = "medium"
                alert = True
            else:
                severity = "high"
                alert = True
            
            return {
                "service_name": service_name,
                "current_budget_remaining_percent": current_budget_remaining_percent,
                "burn_rate_percent_per_day": burn_rate_per_day,
                "days_until_exhaustion": days_until_exhaustion,
                "projected_exhaustion_date": exhaustion_date.isoformat() if exhaustion_date else None,
                "severity": severity,
                "alert_required": alert,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error projecting burn rate: {e}")
            return {"error": str(e)}


# Predefined error budgets for Week 4
DEFAULT_ERROR_BUDGETS = {
    "rag-chatbot-api": {
        "slo_target": 99.9,
        "window_days": 30,
        "description": "RAG Chatbot API availability"
    },
    "document-ingestion": {
        "slo_target": 99.5,
        "window_days": 30,
        "description": "Document ingestion pipeline"
    },
    "compliance-checker": {
        "slo_target": 99.0,
        "window_days": 30,
        "description": "Compliance checking service"
    },
    "vertex-ai-embeddings": {
        "slo_target": 99.9,
        "window_days": 30,
        "description": "Vertex AI embedding generation"
    }
}


# _week4
