"""
Vertex AI Experiment Tracking for RAG system.
Tracks prompt variants, model versions, and hyperparameters.
"""

from typing import Dict, Any, Optional, List
from google.cloud import aiplatform
import time
from app.logging_config import get_logger

logger = get_logger(__name__)


class VertexExperimentTracker:
    """Track experiments in Vertex AI for model and prompt variants."""
    
    def __init__(
        self,
        project: str,
        location: str,
        experiment_name: str = "rag-optimization"
    ):
        """Initialize experiment tracker."""
        self.project = project
        self.location = location
        
        # Initialize Vertex AI
        aiplatform.init(project=project, location=location)
        
        # Create or get experiment
        try:
            self.experiment = aiplatform.Experiment.create(
                experiment_name=experiment_name,
                description="RAG system optimization experiments"
            )
            logger.info(f"Created experiment: {experiment_name}")
        except Exception as e:
            self.experiment = aiplatform.Experiment(experiment_name=experiment_name)
            logger.info(f"Using existing experiment: {experiment_name}")
    
    def start_run(
        self,
        run_name: str,
        params: Dict[str, Any]
    ):
        """
        Start a new experiment run.
        
        Args:
            run_name: Unique name for this run
            params: Hyperparameters to log
        
        Returns:
            ExperimentRun instance
        """
        try:
            run = self.experiment.start_run(run_name)
            
            # Log parameters
            run.log_params(params)
            
            logger.info(
                "Started experiment run",
                extra={"run_name": run_name, "params": params}
            )
            
            return run
            
        except Exception as e:
            logger.error(f"Failed to start experiment run: {e}")
            raise
    
    def log_metrics(
        self,
        run,
        metrics: Dict[str, float],
        step: Optional[int] = None
    ):
        """Log metrics for a run."""
        try:
            run.log_metrics(metrics, step=step)
            logger.debug("Logged metrics", extra={"metrics": metrics, "step": step})
        except Exception as e:
            logger.error(f"Failed to log metrics: {e}")
    
    def log_ragas_results(
        self,
        run,
        ragas_scores: Dict[str, float]
    ):
        """Log RAGAS evaluation results."""
        metrics = {
            "faithfulness": ragas_scores.get("faithfulness", 0.0),
            "answer_relevancy": ragas_scores.get("answer_relevancy", 0.0),
            "context_precision": ragas_scores.get("context_precision", 0.0),
            "context_recall": ragas_scores.get("context_recall", 0.0),
            "answer_correctness": ragas_scores.get("answer_correctness", 0.0)
        }
        self.log_metrics(run, metrics)
    
    def log_performance_metrics(
        self,
        run,
        latency_ms: float,
        tokens_used: int,
        cost_usd: float
    ):
        """Log performance and cost metrics."""
        metrics = {
            "latency_ms": latency_ms,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd
        }
        self.log_metrics(run, metrics)
    
    def end_run(
        self,
        run,
        status: str = "COMPLETED"
    ):
        """End experiment run."""
        try:
            run.end_run()
            logger.info(f"Ended experiment run with status: {status}")
        except Exception as e:
            logger.error(f"Failed to end run: {e}")
    
    def compare_runs(
        self,
        run_names: List[str],
        metric: str = "faithfulness"
    ) -> Dict[str, Any]:
        """
        Compare multiple experiment runs.
        
        Args:
            run_names: List of run names to compare
            metric: Metric to compare
        
        Returns:
            Comparison results
        """
        results = {}
        
        for run_name in run_names:
            try:
                run = self.experiment.get_run(run_name)
                metrics = run.get_metrics()
                results[run_name] = {
                    "metric_value": metrics.get(metric, 0.0),
                    "all_metrics": metrics
                }
            except Exception as e:
                logger.error(f"Failed to get run {run_name}: {e}")
        
        # Find best run
        if results:
            best_run = max(
                results.items(),
                key=lambda x: x[1]["metric_value"]
            )
            
            return {
                "best_run": best_run[0],
                "best_score": best_run[1]["metric_value"],
                "all_results": results
            }
        
        return {"best_run": None, "best_score": 0, "all_results": {}}


class PromptExperimentRunner:
    """Run experiments with different prompt variants."""
    
    def __init__(
        self,
        tracker: VertexExperimentTracker,
        generator,
        evaluator
    ):
        self.tracker = tracker
        self.generator = generator
        self.evaluator = evaluator
    
    async def run_prompt_experiment(
        self,
        prompt_templates: Dict[str, str],
        test_questions: List[str],
        contexts: List[List[str]],
        ground_truths: List[str]
    ) -> Dict[str, Any]:
        """
        Run A/B test on different prompt templates.
        
        Args:
            prompt_templates: Dict of {name: template}
            test_questions: List of test questions
            contexts: Retrieved contexts for each question
            ground_truths: Expected answers
        
        Returns:
            Experiment results
        """
        results = {}
        
        for template_name, template in prompt_templates.items():
            run_name = f"prompt_{template_name}_{int(time.time())}"
            
            # Start experiment run
            run = self.tracker.start_run(
                run_name=run_name,
                params={
                    "prompt_template": template_name,
                    "model": getattr(self.generator, 'model_name', 'unknown'),
                    "num_test_cases": len(test_questions)
                }
            )
            
            # Run evaluation
            total_latency = 0
            total_tokens = 0
            answers = []
            
            for question, context_list in zip(test_questions, contexts):
                start_time = time.time()
                
                # Generate answer with this prompt template
                try:
                    answer = await self.generator.generate_with_template(
                        question=question,
                        contexts=context_list,
                        template=template
                    )
                    
                    latency_ms = (time.time() - start_time) * 1000
                    total_latency += latency_ms
                    total_tokens += answer.get("tokens_used", 0)
                    answers.append(answer.get("text", ""))
                except Exception as e:
                    logger.error(f"Error generating answer: {e}")
                    answers.append("")
            
            # Log results
            self.tracker.log_performance_metrics(
                run,
                latency_ms=total_latency / len(test_questions) if test_questions else 0,
                tokens_used=total_tokens,
                cost_usd=total_tokens * 0.00001  # Approximate
            )
            
            self.tracker.end_run(run)
            
            results[template_name] = {
                "avg_latency_ms": total_latency / len(test_questions) if test_questions else 0,
                "total_tokens": total_tokens
            }
        
        return {
            "results": results
        }
