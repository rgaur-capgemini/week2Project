"""
Vertex AI Experiment Tracker - Week 4
Tracks experiments for prompt variants, model variants, and embedding variants.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
from google.cloud import aiplatform
from app.logging_config import get_logger

logger = get_logger(__name__)


class ExperimentTracker:
    """
    Tracks experiments using Vertex AI Experiments.
    Supports prompt variants, model variants, and embedding variants.
    """
    
    def __init__(self, project: str, location: str, experiment_name: str = "rag-chatbot-experiments"):
        """
        Initialize experiment tracker.
        
        Args:
            project: GCP project ID
            location: GCP region
            experiment_name: Name of the experiment
        """
        self.project = project
        self.location = location
        self.experiment_name = experiment_name
        
        # Initialize Vertex AI
        aiplatform.init(project=project, location=location)
        
        # Get or create experiment
        try:
            self.experiment = aiplatform.Experiment(experiment_name)
            logger.info(f"Using existing experiment: {experiment_name}")
        except:
            self.experiment = aiplatform.Experiment.create(experiment_name)
            logger.info(f"Created new experiment: {experiment_name}")
    
    def start_run(self, run_name: str, variant_type: str, variant_config: Dict[str, Any]) -> str:
        """
        Start a new experiment run.
        
        Args:
            run_name: Name of the run
            variant_type: Type of variant (prompt, model, embedding)
            variant_config: Configuration of the variant
            
        Returns:
            Run ID
        """
        try:
            # Create run
            run = aiplatform.ExperimentRun(run_name, experiment=self.experiment_name)
            
            # Log parameters
            run.log_params({
                "variant_type": variant_type,
                "timestamp": datetime.utcnow().isoformat(),
                **variant_config
            })
            
            logger.info(f"Started experiment run: {run_name}")
            return run_name
            
        except Exception as e:
            logger.error(f"Error starting run: {e}")
            raise
    
    def log_metrics(self, run_name: str, metrics: Dict[str, float]):
        """
        Log metrics for a run.
        
        Args:
            run_name: Name of the run
            metrics: Metrics to log (e.g., latency, accuracy, cost)
        """
        try:
            run = aiplatform.ExperimentRun(run_name, experiment=self.experiment_name)
            run.log_metrics(metrics)
            
            logger.info(f"Logged metrics for run {run_name}: {metrics}")
            
        except Exception as e:
            logger.error(f"Error logging metrics: {e}")
            raise
    
    def log_prompt_variant(
        self,
        variant_name: str,
        prompt_template: str,
        system_instruction: str,
        temperature: float,
        metrics: Dict[str, float]
    ):
        """
        Log a prompt variant experiment.
        
        Args:
            variant_name: Name of the variant
            prompt_template: Prompt template used
            system_instruction: System instruction
            temperature: Temperature setting
            metrics: Performance metrics
        """
        run_name = f"prompt_{variant_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        config = {
            "prompt_template": prompt_template[:200],  # Truncate for logging
            "system_instruction": system_instruction[:200],
            "temperature": temperature
        }
        
        self.start_run(run_name, "prompt", config)
        self.log_metrics(run_name, metrics)
        
        return run_name
    
    def log_model_variant(
        self,
        variant_name: str,
        model_name: str,
        model_params: Dict[str, Any],
        metrics: Dict[str, float]
    ):
        """
        Log a model variant experiment.
        
        Args:
            variant_name: Name of the variant
            model_name: Model identifier (e.g., gemini-pro, gemini-flash)
            model_params: Model parameters
            metrics: Performance metrics
        """
        run_name = f"model_{variant_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        config = {
            "model_name": model_name,
            **model_params
        }
        
        self.start_run(run_name, "model", config)
        self.log_metrics(run_name, metrics)
        
        return run_name
    
    def log_embedding_variant(
        self,
        variant_name: str,
        embedding_model: str,
        embedding_params: Dict[str, Any],
        metrics: Dict[str, float]
    ):
        """
        Log an embedding variant experiment.
        
        Args:
            variant_name: Name of the variant
            embedding_model: Embedding model name
            embedding_params: Embedding parameters
            metrics: Performance metrics
        """
        run_name = f"embedding_{variant_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        config = {
            "embedding_model": embedding_model,
            **embedding_params
        }
        
        self.start_run(run_name, "embedding", config)
        self.log_metrics(run_name, metrics)
        
        return run_name
    
    def compare_runs(self, run_names: List[str]) -> Dict[str, Any]:
        """
        Compare multiple experiment runs.
        
        Args:
            run_names: List of run names to compare
            
        Returns:
            Comparison results
        """
        try:
            comparison = []
            
            for run_name in run_names:
                run = aiplatform.ExperimentRun(run_name, experiment=self.experiment_name)
                
                comparison.append({
                    "run_name": run_name,
                    "params": run.get_params(),
                    "metrics": run.get_metrics()
                })
            
            logger.info(f"Compared {len(run_names)} runs")
            return {
                "runs": comparison,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error comparing runs: {e}")
            raise
    
    def get_best_run(self, metric_name: str, maximize: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get the best run based on a metric.
        
        Args:
            metric_name: Name of the metric to optimize
            maximize: Whether to maximize (True) or minimize (False) the metric
            
        Returns:
            Best run information
        """
        try:
            # Get all runs from experiment
            experiment = aiplatform.Experiment(self.experiment_name)
            runs_df = experiment.get_data_frame()
            
            if runs_df.empty:
                return None
            
            # Find best run
            if metric_name in runs_df.columns:
                if maximize:
                    best_idx = runs_df[metric_name].idxmax()
                else:
                    best_idx = runs_df[metric_name].idxmin()
                
                best_run = runs_df.loc[best_idx].to_dict()
                logger.info(f"Best run for {metric_name}: {best_run}")
                return best_run
            else:
                logger.warning(f"Metric {metric_name} not found in runs")
                return None
                
        except Exception as e:
            logger.error(f"Error getting best run: {e}")
            return None


# _week4
