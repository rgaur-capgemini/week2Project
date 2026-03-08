"""
Vertex AI Model Registry - Week 4
Manages model versions and deployments.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from google.cloud import aiplatform
from app.logging_config import get_logger

logger = get_logger(__name__)


class ModelRegistry:
    """
    Manages model registration and versioning in Vertex AI Model Registry.
    """
    
    def __init__(self, project: str, location: str):
        """
        Initialize model registry.
        
        Args:
            project: GCP project ID
            location: GCP region
        """
        self.project = project
        self.location = location
        aiplatform.init(project=project, location=location)
    
    def register_model(
        self,
        model_name: str,
        model_type: str,
        version: str,
        config: Dict[str, Any],
        metrics: Optional[Dict[str, float]] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Register a model variant in the registry.
        
        Args:
            model_name: Base model name (e.g., "rag-chatbot-gemini")
            model_type: Type (prompt_variant, model_variant, embedding_variant)
            version: Version identifier
            config: Model configuration
            metrics: Performance metrics
            labels: Additional labels
            
        Returns:
            Model resource name
        """
        try:
            # Create model display name
            display_name = f"{model_name}-{model_type}-{version}"
            
            # Prepare labels
            model_labels = {
                "model_type": model_type,
                "version": version.replace(".", "_"),
                "timestamp": datetime.utcnow().strftime("%Y%m%d")
            }
            if labels:
                model_labels.update(labels)
            
            # Upload model (for tracking purposes)
            model = aiplatform.Model.upload(
                display_name=display_name,
                description=f"{model_type} variant v{version}",
                labels=model_labels,
                artifact_uri=f"gs://{self.project}-model-artifacts/{model_name}/{version}",
                serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/tf2-cpu.2-11:latest"
            )
            
            logger.info(f"Registered model: {display_name} (resource: {model.resource_name})")
            return model.resource_name
            
        except Exception as e:
            logger.error(f"Error registering model: {e}")
            raise
    
    def get_model(self, model_name: str, version: Optional[str] = None) -> Optional[aiplatform.Model]:
        """
        Get a model from the registry.
        
        Args:
            model_name: Model name
            version: Specific version (optional)
            
        Returns:
            Model object or None
        """
        try:
            # List models matching name
            models = aiplatform.Model.list(
                filter=f'display_name="{model_name}"',
                order_by="create_time desc"
            )
            
            if not models:
                logger.warning(f"Model {model_name} not found")
                return None
            
            # If version specified, filter by version label
            if version:
                version_label = version.replace(".", "_")
                for model in models:
                    if model.labels.get("version") == version_label:
                        return model
                logger.warning(f"Model {model_name} version {version} not found")
                return None
            
            # Return latest
            return models[0]
            
        except Exception as e:
            logger.error(f"Error getting model: {e}")
            return None
    
    def list_models(self, model_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all registered models.
        
        Args:
            model_type: Filter by model type
            
        Returns:
            List of model information
        """
        try:
            filter_str = f'labels.model_type="{model_type}"' if model_type else None
            models = aiplatform.Model.list(filter=filter_str, order_by="create_time desc")
            
            model_list = []
            for model in models:
                model_list.append({
                    "resource_name": model.resource_name,
                    "display_name": model.display_name,
                    "labels": model.labels,
                    "create_time": model.create_time.isoformat() if model.create_time else None,
                    "update_time": model.update_time.isoformat() if model.update_time else None
                })
            
            logger.info(f"Listed {len(model_list)} models")
            return model_list
            
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    def promote_to_production(self, model_name: str, version: str) -> bool:
        """
        Promote a model version to production.
        
        Args:
            model_name: Model name
            version: Version to promote
            
        Returns:
            Success status
        """
        try:
            model = self.get_model(model_name, version)
            if not model:
                logger.error(f"Model {model_name} v{version} not found")
                return False
            
            # Update labels to mark as production
            current_labels = model.labels or {}
            current_labels["environment"] = "production"
            current_labels["promoted_at"] = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            
            model.update(labels=current_labels)
            
            logger.info(f"Promoted {model_name} v{version} to production")
            return True
            
        except Exception as e:
            logger.error(f"Error promoting model: {e}")
            return False
    
    def get_production_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the current production model.
        
        Args:
            model_name: Base model name
            
        Returns:
            Production model information
        """
        try:
            models = aiplatform.Model.list(
                filter=f'display_name:"{model_name}" AND labels.environment="production"',
                order_by="update_time desc"
            )
            
            if not models:
                logger.warning(f"No production model found for {model_name}")
                return None
            
            prod_model = models[0]
            return {
                "resource_name": prod_model.resource_name,
                "display_name": prod_model.display_name,
                "version": prod_model.labels.get("version", "unknown"),
                "labels": prod_model.labels,
                "promoted_at": prod_model.labels.get("promoted_at")
            }
            
        except Exception as e:
            logger.error(f"Error getting production model: {e}")
            return None
    
    def compare_models(self, model_names: List[str]) -> Dict[str, Any]:
        """
        Compare multiple model versions.
        
        Args:
            model_names: List of model resource names
            
        Returns:
            Comparison data
        """
        try:
            comparison = []
            
            for resource_name in model_names:
                model = aiplatform.Model(resource_name)
                
                comparison.append({
                    "resource_name": resource_name,
                    "display_name": model.display_name,
                    "labels": model.labels,
                    "create_time": model.create_time.isoformat() if model.create_time else None
                })
            
            return {
                "models": comparison,
                "count": len(comparison),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error comparing models: {e}")
            raise


# _week4
