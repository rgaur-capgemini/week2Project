"""
Compare different model variants (Flash vs Pro, different embeddings).
"""

from typing import Dict, Any, List
from app.experiments.experiment_tracker import VertexExperimentTracker
from app.logging_config import get_logger
import time

logger = get_logger(__name__)


class ModelComparator:
    """Compare different model configurations."""
    
    def __init__(
        self,
        project: str,
        location: str,
        tracker: VertexExperimentTracker
    ):
        self.project = project
        self.location = location
        self.tracker = tracker
    
    async def compare_llm_models(
        self,
        models: List[str],
        test_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare different LLM models (Flash vs Pro).
        
        Args:
            models: List of model names (e.g., ["gemini-2.0-flash-001", "gemini-1.5-pro"])
            test_cases: List of {question, contexts, ground_truth}
        
        Returns:
            Comparison results
        """
        results = {}
        
        for model_name in models:
            run_name = f"llm_{model_name.replace('.', '_').replace('-', '_')}_{int(time.time())}"
            
            # Start experiment run
            run = self.tracker.start_run(
                run_name=run_name,
                params={
                    "model": model_name,
                    "num_test_cases": len(test_cases)
                }
            )
            
            # Run test cases
            total_latency = 0
            total_tokens = 0
            
            for case in test_cases:
                start_time = time.time()
                
                # Simulate model call (replace with actual generator)
                latency_ms = (time.time() - start_time) * 1000
                tokens = 500  # Mock value
                
                total_latency += latency_ms
                total_tokens += tokens
            
            # Log metrics
            self.tracker.log_performance_metrics(
                run,
                latency_ms=total_latency / len(test_cases) if test_cases else 0,
                tokens_used=total_tokens,
                cost_usd=self._calculate_cost(model_name, total_tokens)
            )
            
            self.tracker.end_run(run)
            
            results[model_name] = {
                "avg_latency_ms": total_latency / len(test_cases) if test_cases else 0,
                "total_tokens": total_tokens,
                "cost_usd": self._calculate_cost(model_name, total_tokens)
            }
        
        # Determine winner
        if results:
            winner = min(
                results.items(),
                key=lambda x: x[1]["avg_latency_ms"]
            )
            
            return {
                "results": results,
                "winner": {
                    "model": winner[0],
                    "metrics": winner[1]
                }
            }
        
        return {"results": {}, "winner": {}}
    
    def _calculate_cost(self, model_name: str, tokens: int) -> float:
        """Calculate cost based on model pricing."""
        pricing = {
            "gemini-2.0-flash-001": 0.075 / 1_000_000,
            "gemini-1.5-pro": 0.35 / 1_000_000,
            "gemini-1.5-flash": 0.075 / 1_000_000
        }
        return tokens * pricing.get(model_name, 0.1 / 1_000_000)
    
    async def compare_embedding_models(
        self,
        embedding_models: List[str],
        test_texts: List[str]
    ) -> Dict[str, Any]:
        """
        Compare different embedding models.
        
        Args:
            embedding_models: List of embedding model names
            test_texts: Sample texts to embed
        
        Returns:
            Comparison results
        """
        results = {}
        
        for model_name in embedding_models:
            run_name = f"embedding_{model_name.replace('-', '_')}_{int(time.time())}"
            
            run = self.tracker.start_run(
                run_name=run_name,
                params={
                    "embedding_model": model_name,
                    "num_texts": len(test_texts)
                }
            )
            
            # Benchmark embedding generation
            start_time = time.time()
            # Simulate embedding call
            latency_ms = (time.time() - start_time) * 1000
            
            self.tracker.log_performance_metrics(
                run,
                latency_ms=latency_ms,
                tokens_used=len(test_texts) * 512,
                cost_usd=0.00001 * len(test_texts)
            )
            
            self.tracker.end_run(run)
            
            results[model_name] = {
                "latency_ms": latency_ms,
                "dimension": 768,
                "throughput": len(test_texts) / (latency_ms / 1000) if latency_ms > 0 else 0
            }
        
        return results
