"""
Budget Alerts Manager - Week 4
Manages budgets and alerts for cost control.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

# Optional billing imports
try:
    from google.cloud import billing_budgets_v1
    BILLING_BUDGETS_AVAILABLE = True
except ImportError:
    BILLING_BUDGETS_AVAILABLE = False
    billing_budgets_v1 = None

from google.cloud import firestore
from app.logging_config import get_logger

logger = get_logger(__name__)


class BudgetAlertsManager:
    """
    Manages budgets and cost alerts across GCP services.
    """
    
    def __init__(self, project_id: str, billing_account_id: str):
        """
        Initialize budget alerts manager.
        
        Args:
            project_id: GCP project ID
            billing_account_id: Billing account ID
        """
        self.project_id = project_id
        self.billing_account_id = billing_account_id
        self.billing_account_name = f"billingAccounts/{billing_account_id}"
        
        try:
            self.budget_client = billing_budgets_v1.BudgetServiceClient()
        except Exception as e:
            logger.warning(f"Could not initialize budget client: {e}")
            self.budget_client = None
        
        self.db = firestore.Client(project=project_id)
    
    def create_monthly_budget(
        self,
        budget_name: str,
        amount: float,
        threshold_percentages: List[int] = [50, 75, 90, 100],
        notification_channels: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Create a monthly budget with threshold alerts.
        
        Args:
            budget_name: Display name for the budget
            amount: Budget amount in USD
            threshold_percentages: Alert thresholds (e.g., [50, 75, 90, 100])
            notification_channels: Pub/Sub topic or email channels
            
        Returns:
            Budget name/ID or None
        """
        if not self.budget_client:
            logger.error("Budget client not initialized")
            return None
        
        try:
            # Create budget amount
            budget_amount = billing_budgets_v1.BudgetAmount(
                specified_amount=billing_budgets_v1.types.money_pb2.Money(
                    currency_code="USD",
                    units=int(amount)
                )
            )
            
            # Create threshold rules
            threshold_rules = []
            for threshold in threshold_percentages:
                threshold_rules.append(
                    billing_budgets_v1.ThresholdRule(
                        threshold_percent=threshold / 100.0,
                        spend_basis=billing_budgets_v1.ThresholdRule.Basis.CURRENT_SPEND
                    )
                )
            
            # Create budget
            budget = billing_budgets_v1.Budget(
                display_name=budget_name,
                budget_filter=billing_budgets_v1.Filter(
                    projects=[f"projects/{self.project_id}"]
                ),
                amount=budget_amount,
                threshold_rules=threshold_rules
            )
            
            # If notification channels provided, add them
            if notification_channels:
                budget.notifications_rule = billing_budgets_v1.NotificationsRule(
                    pubsub_topic=notification_channels[0] if notification_channels else None,
                    schema_version="1.0"
                )
            
            request = billing_budgets_v1.CreateBudgetRequest(
                parent=self.billing_account_name,
                budget=budget
            )
            
            response = self.budget_client.create_budget(request=request)
            
            logger.info(f"Created budget: {budget_name}")
            
            # Store in Firestore for tracking
            self._store_budget_config(budget_name, amount, threshold_percentages)
            
            return response.name
            
        except Exception as e:
            logger.error(f"Error creating budget: {e}")
            return None
    
    def _store_budget_config(
        self,
        budget_name: str,
        amount: float,
        threshold_percentages: List[int]
    ):
        """Store budget configuration in Firestore for tracking."""
        try:
            self.db.collection("budget_configs").document(budget_name).set({
                "budget_name": budget_name,
                "amount": amount,
                "thresholds": threshold_percentages,
                "created_at": datetime.utcnow(),
                "status": "active"
            })
        except Exception as e:
            logger.error(f"Error storing budget config: {e}")
    
    def list_budgets(self) -> List[Dict[str, Any]]:
        """
        List all budgets for the billing account.
        
        Returns:
            List of budgets
        """
        if not self.budget_client:
            return []
        
        try:
            request = billing_budgets_v1.ListBudgetsRequest(
                parent=self.billing_account_name
            )
            
            budgets = []
            for budget in self.budget_client.list_budgets(request=request):
                budgets.append({
                    "name": budget.name,
                    "display_name": budget.display_name,
                    "amount": budget.amount.specified_amount.units if budget.amount.specified_amount else None,
                    "currency": budget.amount.specified_amount.currency_code if budget.amount.specified_amount else "USD",
                    "thresholds": [int(rule.threshold_percent * 100) for rule in budget.threshold_rules]
                })
            
            return budgets
            
        except Exception as e:
            logger.error(f"Error listing budgets: {e}")
            return []
    
    def create_alert(
        self,
        alert_name: str,
        alert_type: str,
        condition: Dict[str, Any],
        recipients: List[str]
    ) -> str:
        """
        Create a custom cost alert.
        
        Args:
            alert_name: Alert name
            alert_type: Type of alert (threshold, anomaly, forecast)
            condition: Alert conditions
            recipients: Email recipients
            
        Returns:
            Alert ID
        """
        try:
            alert_doc = {
                "alert_id": alert_name,
                "alert_type": alert_type,
                "condition": condition,
                "recipients": recipients,
                "status": "active",
                "created_at": datetime.utcnow(),
                "last_triggered": None,
                "trigger_count": 0
            }
            
            self.db.collection("cost_alerts").document(alert_name).set(alert_doc)
            
            logger.info(f"Created cost alert: {alert_name}")
            return alert_name
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            raise
    
    def check_alerts(self, current_costs: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Check if any alerts should be triggered.
        
        Args:
            current_costs: Current costs by service
            
        Returns:
            List of triggered alerts
        """
        try:
            alerts = self.db.collection("cost_alerts").where("status", "==", "active").stream()
            
            triggered_alerts = []
            
            for alert_doc in alerts:
                alert = alert_doc.to_dict()
                alert_type = alert.get("alert_type")
                condition = alert.get("condition", {})
                
                should_trigger = False
                
                if alert_type == "threshold":
                    service = condition.get("service", "total")
                    threshold = condition.get("threshold", 0)
                    
                    current_cost = current_costs.get(service, 0)
                    
                    if current_cost >= threshold:
                        should_trigger = True
                        triggered_alerts.append({
                            "alert_id": alert.get("alert_id"),
                            "alert_type": alert_type,
                            "service": service,
                            "current_cost": current_cost,
                            "threshold": threshold,
                            "message": f"{service} cost ${current_cost:.2f} exceeded threshold ${threshold:.2f}",
                            "recipients": alert.get("recipients", [])
                        })
                
                if should_trigger:
                    # Update last triggered time
                    self.db.collection("cost_alerts").document(alert_doc.id).update({
                        "last_triggered": datetime.utcnow(),
                        "trigger_count": alert.get("trigger_count", 0) + 1
                    })
            
            return triggered_alerts
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            return []
    
    def get_budget_status(self, budget_name: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a budget.
        
        Args:
            budget_name: Budget name
            
        Returns:
            Budget status with current spend
        """
        try:
            config_doc = self.db.collection("budget_configs").document(budget_name).get()
            if not config_doc.exists:
                return None
            
            config = config_doc.to_dict()
            
            # In real implementation, would fetch actual spend from billing API
            # For now, return config with placeholder spend
            return {
                "budget_name": budget_name,
                "budget_amount": config.get("amount", 0),
                "current_spend": 0.0,  # Would fetch from billing
                "percent_used": 0.0,
                "thresholds": config.get("thresholds", []),
                "status": config.get("status", "active")
            }
            
        except Exception as e:
            logger.error(f"Error getting budget status: {e}")
            return None
    
    def update_budget(self, budget_name: str, new_amount: float) -> bool:
        """
        Update budget amount.
        
        Args:
            budget_name: Budget name
            new_amount: New budget amount
            
        Returns:
            Success status
        """
        try:
            self.db.collection("budget_configs").document(budget_name).update({
                "amount": new_amount,
                "updated_at": datetime.utcnow()
            })
            
            logger.info(f"Updated budget {budget_name} to ${new_amount}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating budget: {e}")
            return False
    
    def delete_alert(self, alert_name: str) -> bool:
        """
        Delete a cost alert.
        
        Args:
            alert_name: Alert name
            
        Returns:
            Success status
        """
        try:
            self.db.collection("cost_alerts").document(alert_name).delete()
            logger.info(f"Deleted alert: {alert_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting alert: {e}")
            return False


# Predefined budget templates
BUDGET_TEMPLATES = {
    "development": {
        "monthly_amount": 500,
        "thresholds": [50, 75, 90, 100],
        "description": "Development environment budget"
    },
    "production": {
        "monthly_amount": 2000,
        "thresholds": [50, 75, 90, 100],
        "description": "Production environment budget"
    },
    "vertex_ai": {
        "monthly_amount": 1000,
        "thresholds": [60, 80, 95, 100],
        "description": "Vertex AI specific budget"
    }
}


# _week4
