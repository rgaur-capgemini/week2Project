"""
Analytics module for tracking usage, latency, and token costs.
Stores metrics in Firestore for real-time analytics.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from google.cloud import firestore
from app.logging_config import get_logger
import statistics

logger = get_logger(__name__)


class AnalyticsTracker:
    """Tracks and analyzes application metrics."""
    
    def __init__(self, project_id: str, collection_name: str = "analytics_metrics"):
        """
        Initialize analytics tracker.
        
        Args:
            project_id: GCP project ID
            collection_name: Firestore collection for metrics
        """
        self.db = firestore.Client(project=project_id)
        self.collection = self.db.collection(collection_name)
        logger.info("Analytics tracker initialized", collection=collection_name)
    
    def track_query(
        self,
        user_email: str,
        query: str,
        response_time_ms: float,
        token_usage: Dict[str, int],
        model: str,
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Track a RAG query execution.
        
        Args:
            user_email: User who made the query
            query: The query text
            response_time_ms: Total response time in milliseconds
            token_usage: Dict with input_tokens, output_tokens, total_tokens
            model: Model used for generation
            success: Whether query was successful
            error: Error message if failed
            metadata: Additional metadata (chunks retrieved, reranking score, etc.)
        """
        doc_data = {
            'type': 'query',
            'user_email': user_email,
            'query': query[:500],  # Store first 500 chars
            'response_time_ms': response_time_ms,
            'token_usage': token_usage,
            'model': model,
            'success': success,
            'error': error,
            'metadata': metadata or {},
            'timestamp': firestore.SERVER_TIMESTAMP,
            'date': datetime.utcnow().date().isoformat(),
            'hour': datetime.utcnow().hour,
        }
        
        # Calculate token cost (approximate - adjust based on actual pricing)
        token_cost = self._calculate_token_cost(token_usage, model)
        doc_data['token_cost_usd'] = token_cost
        
        self.collection.add(doc_data)
        logger.debug("Query tracked", user_email=user_email, response_time_ms=response_time_ms)
    
    def track_document_upload(
        self,
        user_email: str,
        filename: str,
        file_size_bytes: int,
        chunks_created: int,
        processing_time_ms: float,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Track document upload and processing."""
        doc_data = {
            'type': 'document_upload',
            'user_email': user_email,
            'filename': filename,
            'file_size_bytes': file_size_bytes,
            'chunks_created': chunks_created,
            'processing_time_ms': processing_time_ms,
            'success': success,
            'error': error,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'date': datetime.utcnow().date().isoformat(),
        }
        
        self.collection.add(doc_data)
        logger.debug("Document upload tracked", filename=filename, chunks=chunks_created)
    
    def track_user_session(
        self,
        user_email: str,
        session_duration_seconds: int,
        queries_made: int,
        documents_uploaded: int
    ):
        """Track user session summary."""
        doc_data = {
            'type': 'session',
            'user_email': user_email,
            'session_duration_seconds': session_duration_seconds,
            'queries_made': queries_made,
            'documents_uploaded': documents_uploaded,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'date': datetime.utcnow().date().isoformat(),
        }
        
        self.collection.add(doc_data)
    
    def get_usage_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get usage statistics for a time period.
        
        Args:
            start_date: Start of period (default: 7 days ago)
            end_date: End of period (default: now)
            user_email: Filter by specific user (optional)
            
        Returns:
            Usage statistics including query count, tokens, cost
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Build query
        query = self.collection.where('type', '==', 'query')
        
        if user_email:
            query = query.where('user_email', '==', user_email)
        
        # Note: Firestore has limitations on range queries with dates
        # For production, consider using date strings or timestamps
        query = query.where('date', '>=', start_date.date().isoformat())
        query = query.where('date', '<=', end_date.date().isoformat())
        
        docs = query.stream()
        
        # Aggregate statistics
        total_queries = 0
        successful_queries = 0
        failed_queries = 0
        total_tokens = 0
        total_cost = 0.0
        response_times = []
        users = set()
        
        for doc in docs:
            data = doc.to_dict()
            total_queries += 1
            
            if data.get('success', True):
                successful_queries += 1
            else:
                failed_queries += 1
            
            token_usage = data.get('token_usage', {})
            total_tokens += token_usage.get('total_tokens', 0)
            total_cost += data.get('token_cost_usd', 0.0)
            
            if 'response_time_ms' in data:
                response_times.append(data['response_time_ms'])
            
            if 'user_email' in data:
                users.add(data['user_email'])
        
        # Calculate statistics
        stats = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'queries': {
                'total': total_queries,
                'successful': successful_queries,
                'failed': failed_queries,
                'success_rate': successful_queries / total_queries if total_queries > 0 else 0
            },
            'tokens': {
                'total': total_tokens,
                'average_per_query': total_tokens / total_queries if total_queries > 0 else 0
            },
            'cost': {
                'total_usd': round(total_cost, 4),
                'average_per_query_usd': round(total_cost / total_queries, 4) if total_queries > 0 else 0
            },
            'latency': {
                'average_ms': statistics.mean(response_times) if response_times else 0,
                'median_ms': statistics.median(response_times) if response_times else 0,
                'p95_ms': statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else (max(response_times) if response_times else 0),
                'p99_ms': statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else (max(response_times) if response_times else 0),
            },
            'users': {
                'unique_users': len(users),
                'users_list': list(users) if not user_email else [user_email]
            }
        }
        
        logger.info("Usage stats retrieved", total_queries=total_queries, period_days=(end_date - start_date).days)
        return stats
    
    def get_user_usage(self, user_email: str, days: int = 30) -> Dict[str, Any]:
        """Get detailed usage for a specific user."""
        start_date = datetime.utcnow() - timedelta(days=days)
        return self.get_usage_stats(start_date=start_date, user_email=user_email)
    
    def get_hourly_distribution(self, days: int = 7) -> Dict[int, int]:
        """Get query distribution by hour of day."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = self.collection.where('type', '==', 'query')
        query = query.where('date', '>=', start_date.date().isoformat())
        
        hourly_counts = {hour: 0 for hour in range(24)}
        
        for doc in query.stream():
            data = doc.to_dict()
            hour = data.get('hour', 0)
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
        
        return hourly_counts
    
    def get_model_usage(self, days: int = 30) -> Dict[str, Dict[str, Any]]:
        """Get usage statistics per model."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = self.collection.where('type', '==', 'query')
        query = query.where('date', '>=', start_date.date().isoformat())
        
        model_stats = {}
        
        for doc in query.stream():
            data = doc.to_dict()
            model = data.get('model', 'unknown')
            
            if model not in model_stats:
                model_stats[model] = {
                    'query_count': 0,
                    'total_tokens': 0,
                    'total_cost': 0.0,
                    'avg_latency_ms': []
                }
            
            model_stats[model]['query_count'] += 1
            token_usage = data.get('token_usage', {})
            model_stats[model]['total_tokens'] += token_usage.get('total_tokens', 0)
            model_stats[model]['total_cost'] += data.get('token_cost_usd', 0.0)
            
            if 'response_time_ms' in data:
                model_stats[model]['avg_latency_ms'].append(data['response_time_ms'])
        
        # Calculate averages
        for model, stats in model_stats.items():
            if stats['avg_latency_ms']:
                stats['avg_latency_ms'] = statistics.mean(stats['avg_latency_ms'])
            else:
                stats['avg_latency_ms'] = 0
        
        return model_stats
    
    def _calculate_token_cost(self, token_usage: Dict[str, int], model: str) -> float:
        """
        Calculate token cost based on model and usage.
        Prices are approximate and should be updated based on actual GCP pricing.
        """
        # Gemini 2.0 Flash pricing (as of 2024, update as needed)
        pricing = {
            'gemini-2.0-flash': {
                'input': 0.075 / 1_000_000,  # $0.075 per 1M tokens
                'output': 0.30 / 1_000_000,   # $0.30 per 1M tokens
            },
            'gemini-1.5-pro': {
                'input': 1.25 / 1_000_000,
                'output': 5.00 / 1_000_000,
            },
            'gemini-1.5-flash': {
                'input': 0.075 / 1_000_000,
                'output': 0.30 / 1_000_000,
            }
        }
        
        # Find matching pricing
        model_pricing = None
        for key in pricing:
            if key in model:
                model_pricing = pricing[key]
                break
        
        if not model_pricing:
            model_pricing = pricing['gemini-2.0-flash']  # Default
        
        input_tokens = token_usage.get('input_tokens', 0)
        output_tokens = token_usage.get('output_tokens', 0)
        
        cost = (input_tokens * model_pricing['input']) + (output_tokens * model_pricing['output'])
        return cost
    
    def get_top_users(self, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top users by query count."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = self.collection.where('type', '==', 'query')
        query = query.where('date', '>=', start_date.date().isoformat())
        
        user_counts = {}
        
        for doc in query.stream():
            data = doc.to_dict()
            user = data.get('user_email', 'unknown')
            user_counts[user] = user_counts.get(user, 0) + 1
        
        # Sort and limit
        top_users = sorted(
            [{'user_email': user, 'query_count': count} for user, count in user_counts.items()],
            key=lambda x: x['query_count'],
            reverse=True
        )[:limit]
        
        return top_users
