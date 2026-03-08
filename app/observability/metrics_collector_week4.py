"""
Metrics Collector - Week 4
Collects and aggregates metrics for observability.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from google.cloud import monitoring_v3
from google.cloud import firestore
import time
from app.logging_config import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """
    Collects metrics from GCP services and application.
    """
    
    def __init__(self, project_id: str):
        """
        Initialize metrics collector.
        
        Args:
            project_id: GCP project ID
        """
        self.project_id = project_id
        self.project_name = f"projects/{project_id}"
        
        self.monitoring_client = monitoring_v3.MetricServiceClient()
        self.db = firestore.Client(project=project_id)
    
    def record_custom_metric(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        Record a custom metric to Cloud Monitoring.
        
        Args:
            metric_name: Metric name (e.g., "request_latency")
            value: Metric value
            labels: Additional labels
        """
        try:
            series = monitoring_v3.TimeSeries()
            series.metric.type = f"custom.googleapis.com/{metric_name}"
            
            if labels:
                for key, val in labels.items():
                    series.metric.labels[key] = str(val)
            
            series.resource.type = "global"
            series.resource.labels["project_id"] = self.project_id
            
            now = time.time()
            seconds = int(now)
            nanos = int((now - seconds) * 10**9)
            
            interval = monitoring_v3.TimeInterval(
                {"end_time": {"seconds": seconds, "nanos": nanos}}
            )
            
            point = monitoring_v3.Point({
                "interval": interval,
                "value": {"double_value": value}
            })
            
            series.points = [point]
            
            self.monitoring_client.create_time_series(
                name=self.project_name,
                time_series=[series]
            )
            
        except Exception as e:
            logger.error(f"Error recording custom metric: {e}")
    
    def get_gke_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get GKE cluster metrics.
        
        Args:
            hours: Hours to look back
            
        Returns:
            GKE metrics
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            interval = monitoring_v3.TimeInterval({
                "start_time": start_time,
                "end_time": end_time
            })
            
            # CPU utilization
            cpu_filter = (
                'resource.type = "k8s_container" AND '
                'metric.type = "kubernetes.io/container/cpu/core_usage_time"'
            )
            
            results = self.monitoring_client.list_time_series(
                request={
                    "name": self.project_name,
                    "filter": cpu_filter,
                    "interval": interval,
                    "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL
                }
            )
            
            cpu_data = []
            for result in results:
                for point in result.points:
                    cpu_data.append({
                        "timestamp": point.interval.end_time.isoformat(),
                        "value": point.value.double_value
                    })
            
            return {
                "cpu_utilization": cpu_data,
                "period_hours": hours,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting GKE metrics: {e}")
            return {"error": str(e)}
    
    def get_vertex_ai_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get Vertex AI metrics (predictions, latency).
        
        Args:
            hours: Hours to look back
            
        Returns:
            Vertex AI metrics
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            interval = monitoring_v3.TimeInterval({
                "start_time": start_time,
                "end_time": end_time
            })
            
            # Prediction count
            prediction_filter = (
                'resource.type = "aiplatform.googleapis.com/Endpoint" AND '
                'metric.type = "aiplatform.googleapis.com/prediction/prediction_count"'
            )
            
            results = self.monitoring_client.list_time_series(
                request={
                    "name": self.project_name,
                    "filter": prediction_filter,
                    "interval": interval,
                    "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL
                }
            )
            
            prediction_data = []
            for result in results:
                for point in result.points:
                    prediction_data.append({
                        "timestamp": point.interval.end_time.isoformat(),
                        "count": point.value.int64_value
                    })
            
            return {
                "predictions": prediction_data,
                "total_predictions": sum(p["count"] for p in prediction_data),
                "period_hours": hours,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting Vertex AI metrics: {e}")
            return {"error": str(e)}
    
    def get_application_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get application-specific metrics from Firestore.
        
        Args:
            hours: Hours to look back
            
        Returns:
            Application metrics
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Query application metrics collection
            metrics_ref = self.db.collection("application_metrics") \
                .where("timestamp", ">=", cutoff_time) \
                .stream()
            
            metrics = {
                "requests": 0,
                "errors": 0,
                "avg_latency": 0.0,
                "by_endpoint": {}
            }
            
            latencies = []
            
            for doc in metrics_ref:
                data = doc.to_dict()
                
                metrics["requests"] += 1
                if data.get("error"):
                    metrics["errors"] += 1
                
                if "latency_ms" in data:
                    latencies.append(data["latency_ms"])
                
                endpoint = data.get("endpoint", "unknown")
                if endpoint not in metrics["by_endpoint"]:
                    metrics["by_endpoint"][endpoint] = {"count": 0, "errors": 0}
                metrics["by_endpoint"][endpoint]["count"] += 1
                if data.get("error"):
                    metrics["by_endpoint"][endpoint]["errors"] += 1
            
            if latencies:
                metrics["avg_latency"] = sum(latencies) / len(latencies)
                metrics["p50_latency"] = sorted(latencies)[len(latencies) // 2]
                metrics["p95_latency"] = sorted(latencies)[int(len(latencies) * 0.95)]
                metrics["p99_latency"] = sorted(latencies)[int(len(latencies) * 0.99)]
            
            metrics["error_rate"] = (metrics["errors"] / metrics["requests"] * 100) if metrics["requests"] > 0 else 0.0
            
            return {
                "metrics": metrics,
                "period_hours": hours,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting application metrics: {e}")
            return {"error": str(e)}
    
    def record_request_metric(
        self,
        endpoint: str,
        latency_ms: float,
        status_code: int,
        user_id: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """
        Record a request metric for observability.
        
        Args:
            endpoint: API endpoint
            latency_ms: Request latency in milliseconds
            status_code: HTTP status code
            user_id: User making the request
            error_message: Error message if request failed
        """
        try:
            metric_doc = {
                "endpoint": endpoint,
                "latency_ms": latency_ms,
                "status_code": status_code,
                "user_id": user_id or "anonymous",
                "error": status_code >= 400,
                "error_message": error_message,
                "timestamp": datetime.utcnow()
            }
            
            self.db.collection("application_metrics").add(metric_doc)
            
            # Also record to Cloud Monitoring
            self.record_custom_metric(
                "request_latency",
                latency_ms,
                {
                    "endpoint": endpoint,
                    "status": str(status_code)
                }
            )
            
        except Exception as e:
            logger.error(f"Error recording request metric: {e}")
    
    def get_slo_metrics(self) -> Dict[str, Any]:
        """
        Get Service Level Objective (SLO) metrics.
        
        Returns:
            SLO compliance metrics
        """
        try:
            # Get last 24 hours of application metrics
            app_metrics = self.get_application_metrics(24)
            
            metrics = app_metrics.get("metrics", {})
            
            # Calculate availability (target: 99.9%)
            total_requests = metrics.get("requests", 0)
            errors = metrics.get("errors", 0)
            successful_requests = total_requests - errors
            
            availability = (successful_requests / total_requests * 100) if total_requests > 0 else 100.0
            
            # Calculate latency SLO (target: p95 < 500ms)
            p95_latency = metrics.get("p95_latency", 0)
            latency_slo_met = p95_latency < 500
            
            # Error budget (allowing 0.1% errors for 99.9% availability)
            error_budget_allowed = total_requests * 0.001
            error_budget_used = errors
            error_budget_remaining = max(0, error_budget_allowed - error_budget_used)
            error_budget_percent = (error_budget_remaining / error_budget_allowed * 100) if error_budget_allowed > 0 else 100.0
            
            return {
                "availability": {
                    "target": 99.9,
                    "actual": availability,
                    "met": availability >= 99.9,
                    "total_requests": total_requests,
                    "successful_requests": successful_requests,
                    "errors": errors
                },
                "latency": {
                    "target_p95_ms": 500,
                    "actual_p95_ms": p95_latency,
                    "met": latency_slo_met,
                    "avg_latency_ms": metrics.get("avg_latency", 0),
                    "p50_latency_ms": metrics.get("p50_latency", 0),
                    "p99_latency_ms": metrics.get("p99_latency", 0)
                },
                "error_budget": {
                    "allowed": error_budget_allowed,
                    "used": error_budget_used,
                    "remaining": error_budget_remaining,
                    "remaining_percent": error_budget_percent,
                    "status": "healthy" if error_budget_percent > 20 else "critical"
                },
                "period": "24h",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting SLO metrics: {e}")
            return {"error": str(e)}


# _week4
