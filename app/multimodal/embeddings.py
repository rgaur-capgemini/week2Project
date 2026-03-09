"""
Multimodal Embeddings - Week 5
Generate embeddings for text and images using Vertex AI.
"""

from typing import List
from vertexai.vision_models import MultiModalEmbeddingModel
from app.logging_config import get_logger

logger = get_logger(__name__)


class MultiModalEmbedder:
    """Generate multimodal embeddings using Vertex AI"""
    
    def __init__(self):
        self.model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")
        self.dimension = 1408
        logger.info(f"Multimodal embedder initialized (dimension={self.dimension})")
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text"""
        try:
            embeddings = self.model.get_embeddings(
                contextual_text=text
            )
            return embeddings.text_embedding
            
        except Exception as e:
            logger.error(f"Text embedding failed: {e}")
            raise
    
    async def embed_image(self, image_path: str = None, image_gcs_uri: str = None) -> List[float]:
        """
        Generate embedding for image.
        
        Args:
            image_path: Local image path
            image_gcs_uri: GCS URI (gs://...)
        """
        try:
            if image_gcs_uri:
                from vertexai.vision_models import Image
                image = Image.load_from_file(image_gcs_uri)
                embeddings = self.model.get_embeddings(image=image)
            elif image_path:
                from vertexai.vision_models import Image
                image = Image.load_from_file(image_path)
                embeddings = self.model.get_embeddings(image=image)
            else:
                raise ValueError("Either image_path or image_gcs_uri must be provided")
            
            return embeddings.image_embedding
            
        except Exception as e:
            logger.error(f"Image embedding failed: {e}")
            raise
    
    async def embed_multimodal(self, text: str, image_gcs_uri: str) -> List[float]:
        """Generate embedding for text + image"""
        try:
            from vertexai.vision_models import Image
            image = Image.load_from_file(image_gcs_uri)
            
            embeddings = self.model.get_embeddings(
                image=image,
                contextual_text=text
            )
            
            # Returns combined embedding
            return embeddings.image_embedding
            
        except Exception as e:
            logger.error(f"Multimodal embedding failed: {e}")
            raise
