"""
Cost Tracker - Week 4
Tracks costs across all GCP services including Vertex AI tokens.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from google.cloud import bigquery

# Optional billing import
try:
    from google.cloud import billing_v1
    BILLING_AVAILABLE = True
except ImportError:
    BILLING_AVAILABLE = False
    billing_v1 = None

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

from app.logging_config import get_logger

logger = get_logger(__name__)


class CostTracker:
    """
    Tracks costs across GCP services and Vertex AI token usage.
    """
    
    def __init__(self, project_id: str, billing_account_id: Optional[str] = None):
        """
        Initialize cost tracker.
        
        Args:
            project_id: GCP project ID
            billing_account_id: Billing account ID (optional)
        """
        self.project_id = project_id
        self.billing_account_id = billing_account_id
        self.bq_client = bigquery.Client(project=project_id)
        
        if billing_account_id:
            self.billing_client = billing_v1.CloudBillingClient()
    
    def get_current_month_costs(self) -> Dict[str, Any]:
        """
        Get costs for the current month.
        
        Returns:
            Cost breakdown by service
        """
        try:
            # Query billing export table (assumes billing export is configured)
            query = f"""
            SELECT
                service.description as service_name,
                SUM(cost) as total_cost,
                SUM(CASE WHEN usage_start_time >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY) 
                    THEN cost ELSE 0 END) as daily_cost,
                currency
            FROM `{self.project_id}.billing_export.gcp_billing_export_v1_*`
            WHERE DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
                AND project.id = @project_id
            GROUP BY service_name, currency
            ORDER BY total_cost DESC
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("project_id", "STRING", self.project_id)
                ]
            )
            
            results = self.bq_client.query(query, job_config=job_config).result()
            
            costs = []
            total_cost = 0.0
            currency = "USD"
            
            for row in results:
                costs.append({
                    "service": row.service_name,
                    "total_cost": float(row.total_cost),
                    "daily_cost": float(row.daily_cost),
                    "currency": row.currency
                })
                total_cost += float(row.total_cost)
                currency = row.currency
            
            return {
                "period": "current_month",
                "total_cost": total_cost,
                "currency": currency,
                "breakdown": costs,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting current month costs: {e}")
            return {
                "period": "current_month",
                "total_cost": 0.0,
                "currency": "USD",
                "breakdown": [],
                "error": str(e)
            }
    
    def get_cost_by_service(self, service_name: str, days: int = 30) -> Dict[str, Any]:
        """
        Get costs for a specific service over time.
        
        Args:
            service_name: Service name (e.g., "Vertex AI", "Cloud Storage")
            days: Number of days to look back
            
        Returns:
            Time series cost data
        """
        try:
            query = f"""
            SELECT
                DATE(usage_start_time) as date,
                SUM(cost) as cost,
                currency
            FROM `{self.project_id}.billing_export.gcp_billing_export_v1_*`
            WHERE service.description = @service_name
                AND project.id = @project_id
                AND DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
            GROUP BY date, currency
            ORDER BY date DESC
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("service_name", "STRING", service_name),
                    bigquery.ScalarQueryParameter("project_id", "STRING", self.project_id),
                    bigquery.ScalarQueryParameter("days", "INT64", days)
                ]
            )
            
            results = self.bq_client.query(query, job_config=job_config).result()
            
            daily_costs = []
            for row in results:
                daily_costs.append({
                    "date": row.date.isoformat(),
                    "cost": float(row.cost),
                    "currency": row.currency
                })
            
            total_cost = sum(item["cost"] for item in daily_costs)
            
            return {
                "service": service_name,
                "period_days": days,
                "total_cost": total_cost,
                "daily_costs": daily_costs,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting service costs: {e}")
            return {
                "service": service_name,
                "period_days": days,
                "total_cost": 0.0,
                "daily_costs": [],
                "error": str(e)
            }
    
    def get_vertex_ai_token_usage(self, days: int = 30) -> Dict[str, Any]:
        """
        Get Vertex AI token usage and costs.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Token usage and cost breakdown
        """
        try:
            query = f"""
            SELECT
                DATE(usage_start_time) as date,
                sku.description as sku_description,
                SUM(usage.amount) as usage_amount,
                usage.unit as usage_unit,
                SUM(cost) as cost,
                currency
            FROM `{self.project_id}.billing_export.gcp_billing_export_v1_*`
            WHERE service.description = 'Vertex AI'
                AND project.id = @project_id
                AND DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
                AND (sku.description LIKE '%token%' OR sku.description LIKE '%prediction%')
            GROUP BY date, sku_description, usage_unit, currency
            ORDER BY date DESC, cost DESC
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("project_id", "STRING", self.project_id),
                    bigquery.ScalarQueryParameter("days", "INT64", days)
                ]
            )
            
            results = self.bq_client.query(query, job_config=job_config).result()
            
            usage_data = []
            total_cost = 0.0
            total_tokens = 0
            
            for row in results:
                usage_data.append({
                    "date": row.date.isoformat(),
                    "sku": row.sku_description,
                    "usage_amount": float(row.usage_amount),
                    "usage_unit": row.usage_unit,
                    "cost": float(row.cost),
                    "currency": row.currency
                })
                total_cost += float(row.cost)
                if "token" in row.usage_unit.lower():
                    total_tokens += int(row.usage_amount)
            
            return {
                "service": "Vertex AI",
                "period_days": days,
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "usage_breakdown": usage_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting token usage: {e}")
            return {
                "service": "Vertex AI",
                "period_days": days,
                "total_cost": 0.0,
                "total_tokens": 0,
                "usage_breakdown": [],
                "error": str(e)
            }
    
    def get_cost_forecast(self, days_ahead: int = 30) -> Dict[str, Any]:
        """
        Forecast costs for upcoming days based on historical trends.
        
        Args:
            days_ahead: Number of days to forecast
            
        Returns:
            Cost forecast
        """
        try:
            # Get last 60 days of costs
            query = f"""
            SELECT
                DATE(usage_start_time) as date,
                SUM(cost) as daily_cost
            FROM `{self.project_id}.billing_export.gcp_billing_export_v1_*`
            WHERE project.id = @project_id
                AND DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
            GROUP BY date
            ORDER BY date ASC
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("project_id", "STRING", self.project_id)
                ]
            )
            
            results = self.bq_client.query(query, job_config=job_config).result()
            
            # Convert to pandas for easier analysis
            data = []
            for row in results:
                data.append({
                    "date": row.date,
                    "cost": float(row.daily_cost)
                })
            
            if not data:
                return {
                    "forecast_days": days_ahead,
                    "forecasted_total": 0.0,
                    "daily_forecast": [],
                    "error": "No historical data available"
                }
            
            df = pd.DataFrame(data)
            
            # Simple moving average forecast
            avg_daily_cost = df["cost"].mean()
            forecasted_total = avg_daily_cost * days_ahead
            
            # Generate daily forecast
            today = datetime.now().date()
            daily_forecast = []
            for i in range(1, days_ahead + 1):
                forecast_date = today + timedelta(days=i)
                daily_forecast.append({
                    "date": forecast_date.isoformat(),
                    "forecasted_cost": avg_daily_cost
                })
            
            return {
                "forecast_days": days_ahead,
                "forecasted_total": forecasted_total,
                "average_daily_cost": avg_daily_cost,
                "daily_forecast": daily_forecast,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error forecasting costs: {e}")
            return {
                "forecast_days": days_ahead,
                "forecasted_total": 0.0,
                "daily_forecast": [],
                "error": str(e)
            }
    
    def get_cost_anomalies(self, threshold_percent: float = 50.0) -> List[Dict[str, Any]]:
        """
        Detect cost anomalies (unusual spikes).
        
        Args:
            threshold_percent: Percentage increase to flag as anomaly
            
        Returns:
            List of detected anomalies
        """
        try:
            query = f"""
            WITH daily_costs AS (
                SELECT
                    DATE(usage_start_time) as date,
                    SUM(cost) as daily_cost
                FROM `{self.project_id}.billing_export.gcp_billing_export_v1_*`
                WHERE project.id = @project_id
                    AND DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
                GROUP BY date
            ),
            cost_with_avg AS (
                SELECT
                    date,
                    daily_cost,
                    AVG(daily_cost) OVER (ORDER BY date ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) as avg_cost
                FROM daily_costs
            )
            SELECT
                date,
                daily_cost,
                avg_cost,
                ((daily_cost - avg_cost) / avg_cost * 100) as percent_increase
            FROM cost_with_avg
            WHERE avg_cost > 0
                AND ((daily_cost - avg_cost) / avg_cost * 100) > @threshold
            ORDER BY date DESC
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("project_id", "STRING", self.project_id),
                    bigquery.ScalarQueryParameter("threshold", "FLOAT64", threshold_percent)
                ]
            )
            
            results = self.bq_client.query(query, job_config=job_config).result()
            
            anomalies = []
            for row in results:
                anomalies.append({
                    "date": row.date.isoformat(),
                    "daily_cost": float(row.daily_cost),
                    "average_cost": float(row.avg_cost),
                    "percent_increase": float(row.percent_increase),
                    "severity": "high" if row.percent_increase > 100 else "medium"
                })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []


# _week4
