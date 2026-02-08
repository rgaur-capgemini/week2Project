"""
Analytics and metrics collection system.
Tracks usage, latency, token costs, and system performance.
"""

import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

import redis
from redis import Redis
from redis.exceptions import RedisError

from app.logging_config import get_logger
from app.config import config

logger = get_logger(__name__)


class AnalyticsCollector:
    """
    Real-time analytics collector using Redis.
    
    Metrics tracked:
    - API call counts (by endpoint, user, status)
    - Latency statistics (p50, p95, p99)
    - Token usage and costs
    - Error rates
    - User activity
    """
    
    # Token pricing (per 1M tokens) - Gemini 2.0 Flash
    TOKEN_PRICING = {
        "input": 0.075,   # $0.075 per 1M input tokens
        "output": 0.30    # $0.30 per 1M output tokens
    }
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        db: int = 1  # Use different DB than chat history
    ):
        """Initialize analytics collector."""
        self.host = host or config.get_env("REDIS_HOST", "10.168.174.3")
        self.port = port or int(config.get_env("REDIS_PORT", "6379"))
        self.db = db
        
        # Get password from Secret Manager
        self.password = password
        if not self.password:
            try:
                self.password = config.get_secret("redis-password")
            except Exception:
                self.password = None
        
        # Initialize Redis
        self.client: Optional[Redis] = None
        self._connect()
    
    def _connect(self):
        """Establish Redis connection."""
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            self.client.ping()
            logger.info("Analytics Redis connection established")
            
        except RedisError as e:
            logger.error(f"Analytics Redis connection failed: {e}")
            self.client = None
    
    def record_api_call(
        self,
        endpoint: str,
        method: str,
        user_id: str,
        status_code: int,
        latency_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record an API call for analytics.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            user_id: User identifier
            status_code: HTTP status code
            latency_ms: Request latency in milliseconds
            metadata: Additional metadata
        """
        if not self.client:
            return
        
        try:
            timestamp = time.time()
            date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
            hour_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d-%H")
            
            # Increment counters
            self.client.hincrby(f"api:calls:{date_str}", endpoint, 1)
            self.client.hincrby(f"api:calls:user:{user_id}:{date_str}", endpoint, 1)
            self.client.hincrby(f"api:status:{date_str}", str(status_code), 1)
            self.client.hincrby(f"api:method:{date_str}", method, 1)
            
            # Record latency (use sorted set for percentile calculations)
            latency_key = f"api:latency:{endpoint}:{hour_str}"
            self.client.zadd(latency_key, {f"{timestamp}:{latency_ms}": latency_ms})
            self.client.expire(latency_key, 86400 * 7)  # Keep for 7 days
            
            # Record in time series
            call_data = {
                "endpoint": endpoint,
                "method": method,
                "user_id": user_id,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "timestamp": timestamp,
                "metadata": metadata or {}
            }
            
            ts_key = f"api:timeseries:{date_str}"
            self.client.lpush(ts_key, json.dumps(call_data))
            self.client.ltrim(ts_key, 0, 9999)  # Keep last 10k entries
            self.client.expire(ts_key, 86400 * 30)  # Keep for 30 days
            
            # Set daily key expiration
            self.client.expire(f"api:calls:{date_str}", 86400 * 90)
            self.client.expire(f"api:status:{date_str}", 86400 * 90)
            self.client.expire(f"api:method:{date_str}", 86400 * 90)
            
        except RedisError as e:
            logger.error(f"Failed to record API call: {e}")
    
    def record_tokens(
        self,
        user_id: str,
        endpoint: str,
        prompt_tokens: int,
        completion_tokens: int,
        model: str
    ):
        """
        Record token usage and calculate cost.
        
        Args:
            user_id: User identifier
            endpoint: API endpoint
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            model: Model name
        """
        if not self.client:
            return
        
        try:
            timestamp = time.time()
            date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
            
            total_tokens = prompt_tokens + completion_tokens
            
            # Calculate cost (in dollars)
            cost = (
                (prompt_tokens / 1_000_000) * self.TOKEN_PRICING["input"] +
                (completion_tokens / 1_000_000) * self.TOKEN_PRICING["output"]
            )
            
            # Increment token counters
            self.client.hincrby(f"tokens:usage:{date_str}", "prompt_tokens", prompt_tokens)
            self.client.hincrby(f"tokens:usage:{date_str}", "completion_tokens", completion_tokens)
            self.client.hincrby(f"tokens:usage:{date_str}", "total_tokens", total_tokens)
            
            # Per-user tokens
            self.client.hincrby(f"tokens:user:{user_id}:{date_str}", "prompt_tokens", prompt_tokens)
            self.client.hincrby(f"tokens:user:{user_id}:{date_str}", "completion_tokens", completion_tokens)
            self.client.hincrby(f"tokens:user:{user_id}:{date_str}", "total_tokens", total_tokens)
            
            # Increment cost (store as cents to avoid floating point issues)
            cost_cents = int(cost * 100)
            self.client.hincrby(f"tokens:cost:{date_str}", "total_cost_cents", cost_cents)
            self.client.hincrby(f"tokens:cost:user:{user_id}:{date_str}", "total_cost_cents", cost_cents)
            
            # Per-endpoint tokens
            self.client.hincrby(f"tokens:endpoint:{endpoint}:{date_str}", "total_tokens", total_tokens)
            
            # Set expiration
            self.client.expire(f"tokens:usage:{date_str}", 86400 * 90)
            self.client.expire(f"tokens:cost:{date_str}", 86400 * 90)
            
            logger.debug(
                "Tokens recorded",
                user_id=user_id,
                endpoint=endpoint,
                tokens=total_tokens,
                cost_usd=f"${cost:.6f}"
            )
            
        except RedisError as e:
            logger.error(f"Failed to record tokens: {e}")
    
    def get_usage_stats(
        self,
        date: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get usage statistics.
        
        Args:
            date: Date string (YYYY-MM-DD), defaults to today
            user_id: Optional user filter
        
        Returns:
            Usage statistics
        """
        if not self.client:
            return {}
        
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            stats = {}
            
            # API call counts
            if user_id:
                calls_key = f"api:calls:user:{user_id}:{date}"
            else:
                calls_key = f"api:calls:{date}"
            
            calls = self.client.hgetall(calls_key)
            stats["api_calls"] = {k: int(v) for k, v in calls.items()}
            stats["total_calls"] = sum(int(v) for v in calls.values())
            
            # Status codes
            statuses = self.client.hgetall(f"api:status:{date}")
            stats["status_codes"] = {k: int(v) for k, v in statuses.items()}
            
            # Methods
            methods = self.client.hgetall(f"api:method:{date}")
            stats["methods"] = {k: int(v) for k, v in methods.items()}
            
            # Token usage
            if user_id:
                tokens_key = f"tokens:user:{user_id}:{date}"
                cost_key = f"tokens:cost:user:{user_id}:{date}"
            else:
                tokens_key = f"tokens:usage:{date}"
                cost_key = f"tokens:cost:{date}"
            
            tokens = self.client.hgetall(tokens_key)
            stats["tokens"] = {k: int(v) for k, v in tokens.items()}
            
            # Cost
            cost_data = self.client.hgetall(cost_key)
            if cost_data:
                cost_cents = int(cost_data.get("total_cost_cents", 0))
                stats["cost_usd"] = cost_cents / 100.0
            else:
                stats["cost_usd"] = 0.0
            
            return stats
            
        except RedisError as e:
            logger.error(f"Failed to get usage stats: {e}")
            return {}
    
    def get_latency_stats(
        self,
        endpoint: str,
        hours: int = 1
    ) -> Dict[str, float]:
        """
        Get latency statistics for an endpoint.
        
        Args:
            endpoint: API endpoint
            hours: Number of hours to look back
        
        Returns:
            Latency percentiles (p50, p95, p99, mean, max)
        """
        if not self.client:
            return {}
        
        try:
            # Collect latencies from recent hours
            now = datetime.now()
            all_latencies = []
            
            for i in range(hours):
                hour = (now - timedelta(hours=i)).strftime("%Y-%m-%d-%H")
                key = f"api:latency:{endpoint}:{hour}"
                
                # Get all latencies from sorted set
                entries = self.client.zrange(key, 0, -1, withscores=True)
                latencies = [score for _, score in entries]
                all_latencies.extend(latencies)
            
            if not all_latencies:
                return {
                    "p50": 0,
                    "p95": 0,
                    "p99": 0,
                    "mean": 0,
                    "max": 0,
                    "min": 0,
                    "count": 0
                }
            
            # Sort for percentile calculation
            sorted_latencies = sorted(all_latencies)
            count = len(sorted_latencies)
            
            def percentile(data, p):
                index = int((p / 100) * len(data))
                return data[min(index, len(data) - 1)]
            
            stats = {
                "p50": percentile(sorted_latencies, 50),
                "p95": percentile(sorted_latencies, 95),
                "p99": percentile(sorted_latencies, 99),
                "mean": sum(sorted_latencies) / count,
                "max": max(sorted_latencies),
                "min": min(sorted_latencies),
                "count": count
            }
            
            return stats
            
        except RedisError as e:
            logger.error(f"Failed to get latency stats: {e}")
            return {}
    
    def get_user_activity(
        self,
        user_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get user activity summary.
        
        Args:
            user_id: User identifier
            days: Number of days to look back
        
        Returns:
            User activity statistics
        """
        if not self.client:
            return {}
        
        try:
            activity = {
                "user_id": user_id,
                "daily_stats": []
            }
            
            total_calls = 0
            total_tokens = 0
            total_cost = 0.0
            
            for i in range(days):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                
                # Get daily stats
                day_stats = self.get_usage_stats(date=date, user_id=user_id)
                
                daily_data = {
                    "date": date,
                    "calls": day_stats.get("total_calls", 0),
                    "tokens": day_stats.get("tokens", {}).get("total_tokens", 0),
                    "cost_usd": day_stats.get("cost_usd", 0.0)
                }
                
                activity["daily_stats"].append(daily_data)
                
                total_calls += daily_data["calls"]
                total_tokens += daily_data["tokens"]
                total_cost += daily_data["cost_usd"]
            
            activity["totals"] = {
                "calls": total_calls,
                "tokens": total_tokens,
                "cost_usd": total_cost
            }
            
            return activity
            
        except RedisError as e:
            logger.error(f"Failed to get user activity: {e}")
            return {}
    
    def get_system_overview(self) -> Dict[str, Any]:
        """
        Get system-wide analytics overview.
        
        Returns:
            System metrics and health indicators
        """
        if not self.client:
            return {}
        
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Get today's usage
            today_stats = self.get_usage_stats(date=today)
            
            # Get unique users (approximate using key scan)
            user_keys = []
            for key in self.client.scan_iter(f"tokens:user:*:{today}"):
                user_keys.append(key)
            
            unique_users = len(set(
                key.split(":")[2] for key in user_keys if len(key.split(":")) >= 3
            ))
            
            # Error rate
            total_calls = today_stats.get("total_calls", 0)
            error_calls = sum(
                count for status, count in today_stats.get("status_codes", {}).items()
                if int(status) >= 400
            )
            error_rate = (error_calls / total_calls * 100) if total_calls > 0 else 0
            
            # Get latency for main endpoints
            query_latency = self.get_latency_stats("/query", hours=1)
            ingest_latency = self.get_latency_stats("/ingest", hours=1)
            
            overview = {
                "date": today,
                "total_requests": total_calls,
                "unique_users": unique_users,
                "error_rate": round(error_rate, 2),
                "total_tokens": today_stats.get("tokens", {}).get("total_tokens", 0),
                "total_cost_usd": today_stats.get("cost_usd", 0.0),
                "latency": {
                    "query": query_latency,
                    "ingest": ingest_latency
                },
                "status_distribution": today_stats.get("status_codes", {})
            }
            
            return overview
            
        except RedisError as e:
            logger.error(f"Failed to get system overview: {e}")
            return {}
    
    def health_check(self) -> bool:
        """Check if analytics system is healthy."""
        if not self.client:
            return False
        
        try:
            self.client.ping()
            return True
        except RedisError:
            return False
