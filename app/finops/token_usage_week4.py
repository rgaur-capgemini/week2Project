"""
Token Usage Tracker - Week 4
Tracks Vertex AI token usage in real-time.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from google.cloud import firestore
from app.logging_config import get_logger

logger = get_logger(__name__)


class TokenUsageTracker:
    """
    Tracks Vertex AI token usage for cost optimization.
    """
    
    def __init__(self, firestore_client):
        """
        Initialize token usage tracker.
        
        Args:
            firestore_client: Firestore client instance
        """
        self.db = firestore_client
        self.usage_collection = "token_usage"
    
    def record_usage(
        self,
        user_id: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        request_type: str = "chat",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record token usage for a request.
        
        Args:
            user_id: User making the request
            model_name: Model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost: Estimated cost
            request_type: Type of request (chat, embedding, etc.)
            metadata: Additional metadata
        """
        try:
            usage_doc = {
                "user_id": user_id,
                "model_name": model_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost": cost,
                "request_type": request_type,
                "timestamp": datetime.utcnow(),
                "metadata": metadata or {}
            }
            
            self.db.collection(self.usage_collection).add(usage_doc)
            
            # Update daily aggregates
            self._update_daily_aggregate(
                user_id, model_name, input_tokens, output_tokens, cost, request_type
            )
            
        except Exception as e:
            logger.error(f"Error recording token usage: {e}")
    
    def _update_daily_aggregate(
        self,
        user_id: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        request_type: str
    ):
        """Update daily token usage aggregates."""
        try:
            today = datetime.utcnow().date().isoformat()
            aggregate_id = f"{user_id}_{today}_{model_name}_{request_type}"
            
            aggregate_ref = self.db.collection("token_usage_daily").document(aggregate_id)
            aggregate_doc = aggregate_ref.get()
            
            if aggregate_doc.exists:
                # Update existing aggregate
                current = aggregate_doc.to_dict()
                aggregate_ref.update({
                    "input_tokens": current.get("input_tokens", 0) + input_tokens,
                    "output_tokens": current.get("output_tokens", 0) + output_tokens,
                    "total_tokens": current.get("total_tokens", 0) + input_tokens + output_tokens,
                    "cost": current.get("cost", 0.0) + cost,
                    "request_count": current.get("request_count", 0) + 1,
                    "updated_at": datetime.utcnow()
                })
            else:
                # Create new aggregate
                aggregate_ref.set({
                    "user_id": user_id,
                    "date": today,
                    "model_name": model_name,
                    "request_type": request_type,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "cost": cost,
                    "request_count": 1,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
                
        except Exception as e:
            logger.error(f"Error updating daily aggregate: {e}")
    
    def get_user_usage(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get token usage for a specific user.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            Usage statistics
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
            
            aggregates = self.db.collection("token_usage_daily") \
                .where("user_id", "==", user_id) \
                .where("date", ">=", cutoff_date) \
                .stream()
            
            total_input = 0
            total_output = 0
            total_cost = 0.0
            total_requests = 0
            by_model = {}
            by_type = {}
            
            for doc in aggregates:
                data = doc.to_dict()
                
                total_input += data.get("input_tokens", 0)
                total_output += data.get("output_tokens", 0)
                total_cost += data.get("cost", 0.0)
                total_requests += data.get("request_count", 0)
                
                # Aggregate by model
                model = data.get("model_name", "unknown")
                if model not in by_model:
                    by_model[model] = {"tokens": 0, "cost": 0.0, "requests": 0}
                by_model[model]["tokens"] += data.get("total_tokens", 0)
                by_model[model]["cost"] += data.get("cost", 0.0)
                by_model[model]["requests"] += data.get("request_count", 0)
                
                # Aggregate by type
                req_type = data.get("request_type", "unknown")
                if req_type not in by_type:
                    by_type[req_type] = {"tokens": 0, "cost": 0.0, "requests": 0}
                by_type[req_type]["tokens"] += data.get("total_tokens", 0)
                by_type[req_type]["cost"] += data.get("cost", 0.0)
                by_type[req_type]["requests"] += data.get("request_count", 0)
            
            return {
                "user_id": user_id,
                "period_days": days,
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_tokens": total_input + total_output,
                "total_cost": total_cost,
                "total_requests": total_requests,
                "by_model": by_model,
                "by_request_type": by_type,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting user usage: {e}")
            return {
                "user_id": user_id,
                "period_days": days,
                "total_tokens": 0,
                "total_cost": 0.0,
                "error": str(e)
            }
    
    def get_project_usage(self, days: int = 30) -> Dict[str, Any]:
        """
        Get token usage for entire project.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Aggregate usage statistics
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
            
            aggregates = self.db.collection("token_usage_daily") \
                .where("date", ">=", cutoff_date) \
                .stream()
            
            total_tokens = 0
            total_cost = 0.0
            total_requests = 0
            by_user = {}
            by_model = {}
            daily_usage = {}
            
            for doc in aggregates:
                data = doc.to_dict()
                
                total_tokens += data.get("total_tokens", 0)
                total_cost += data.get("cost", 0.0)
                total_requests += data.get("request_count", 0)
                
                # By user
                user = data.get("user_id", "unknown")
                if user not in by_user:
                    by_user[user] = {"tokens": 0, "cost": 0.0, "requests": 0}
                by_user[user]["tokens"] += data.get("total_tokens", 0)
                by_user[user]["cost"] += data.get("cost", 0.0)
                by_user[user]["requests"] += data.get("request_count", 0)
                
                # By model
                model = data.get("model_name", "unknown")
                if model not in by_model:
                    by_model[model] = {"tokens": 0, "cost": 0.0, "requests": 0}
                by_model[model]["tokens"] += data.get("total_tokens", 0)
                by_model[model]["cost"] += data.get("cost", 0.0)
                by_model[model]["requests"] += data.get("request_count", 0)
                
                # Daily totals
                date = data.get("date", "unknown")
                if date not in daily_usage:
                    daily_usage[date] = {"tokens": 0, "cost": 0.0, "requests": 0}
                daily_usage[date]["tokens"] += data.get("total_tokens", 0)
                daily_usage[date]["cost"] += data.get("cost", 0.0)
                daily_usage[date]["requests"] += data.get("request_count", 0)
            
            return {
                "period_days": days,
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "total_requests": total_requests,
                "by_user": by_user,
                "by_model": by_model,
                "daily_usage": daily_usage,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting project usage: {e}")
            return {
                "period_days": days,
                "total_tokens": 0,
                "total_cost": 0.0,
                "error": str(e)
            }
    
    def get_top_users(self, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top token users.
        
        Args:
            days: Number of days to look back
            limit: Number of top users to return
            
        Returns:
            List of top users by token usage
        """
        try:
            project_usage = self.get_project_usage(days)
            by_user = project_usage.get("by_user", {})
            
            # Sort by tokens
            top_users = sorted(
                [{"user_id": k, **v} for k, v in by_user.items()],
                key=lambda x: x["tokens"],
                reverse=True
            )[:limit]
            
            return top_users
            
        except Exception as e:
            logger.error(f"Error getting top users: {e}")
            return []
    
    def estimate_cost(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Estimate cost for token usage.
        
        Args:
            model_name: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Estimated cost in USD
        """
        # Pricing as of 2024 (approximate)
        pricing = {
            "gemini-1.5-pro-002": {
                "input": 0.00025,  # per 1K tokens
                "output": 0.00075
            },
            "gemini-1.5-flash-002": {
                "input": 0.0000375,
                "output": 0.00015
            },
            "textembedding-gecko@003": {
                "input": 0.00001,
                "output": 0.0
            }
        }
        
        # Default pricing
        model_pricing = pricing.get(model_name, {"input": 0.0001, "output": 0.0003})
        
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]
        
        return input_cost + output_cost
    
    def check_usage_limits(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user is approaching usage limits.
        
        Args:
            user_id: User ID
            
        Returns:
            Limit status
        """
        try:
            # Get user's usage for current month
            today = datetime.utcnow()
            first_day = today.replace(day=1)
            days_in_month = (today - first_day).days + 1
            
            usage = self.get_user_usage(user_id, days=days_in_month)
            
            # Define limits (could be configurable)
            DAILY_TOKEN_LIMIT = 100000
            MONTHLY_TOKEN_LIMIT = 1000000
            MONTHLY_COST_LIMIT = 50.0
            
            daily_avg = usage["total_tokens"] / days_in_month if days_in_month > 0 else 0
            
            warnings = []
            
            if daily_avg > DAILY_TOKEN_LIMIT * 0.8:
                warnings.append(f"Approaching daily token limit: {daily_avg:.0f}/{DAILY_TOKEN_LIMIT}")
            
            if usage["total_tokens"] > MONTHLY_TOKEN_LIMIT * 0.8:
                warnings.append(f"Approaching monthly token limit: {usage['total_tokens']}/{MONTHLY_TOKEN_LIMIT}")
            
            if usage["total_cost"] > MONTHLY_COST_LIMIT * 0.8:
                warnings.append(f"Approaching monthly cost limit: ${usage['total_cost']:.2f}/${MONTHLY_COST_LIMIT}")
            
            return {
                "user_id": user_id,
                "within_limits": len(warnings) == 0,
                "warnings": warnings,
                "usage": {
                    "tokens": usage["total_tokens"],
                    "cost": usage["total_cost"],
                    "daily_average": daily_avg
                },
                "limits": {
                    "daily_tokens": DAILY_TOKEN_LIMIT,
                    "monthly_tokens": MONTHLY_TOKEN_LIMIT,
                    "monthly_cost": MONTHLY_COST_LIMIT
                }
            }
            
        except Exception as e:
            logger.error(f"Error checking usage limits: {e}")
            return {
                "user_id": user_id,
                "within_limits": True,
                "warnings": [],
                "error": str(e)
            }


# _week4
