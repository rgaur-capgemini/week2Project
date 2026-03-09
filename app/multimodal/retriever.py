"""
Multimodal Retriever - Week 5
Unified search across text and images.
"""

from typing import List, Dict
from app.multimodal.embeddings import MultiModalEmbedder
from app.multimodal.vector_store import MultiModalVectorStore
from app.multimodal.image_store import ImageStore
from app.logging_config import get_logger

logger = get_logger(__name__)


class MultiModalRetriever:
    """Unified retrieval for text and image content"""
    
    def __init__(self):
        self.embedder = MultiModalEmbedder()
        self.vector_store = MultiModalVectorStore()
        self.image_store = ImageStore()
        logger.info("Multimodal retriever initialized")
    
    async def search_by_text(self, query: str, top_k: int = 10, vector_type: str = None) -> List[Dict]:
        """
        Search using text query.
        
        Args:
            query: Text query
            top_k: Number of results
            vector_type: Filter by type ("image", "text", "multimodal") or None for all
        """
        try:
            logger.info(f"Text search: query='{query}', top_k={top_k}, type={vector_type}")
            
            # Generate query embedding
            query_embedding = await self.embedder.embed_text(query)
            
            # Search vectors
            results = await self.vector_store.search(
                query_embedding=query_embedding,
                top_k=top_k,
                vector_type=vector_type
            )
            
            # Enrich results with image metadata
            enriched_results = []
            for result in results:
                if result["vector_type"] == "image":
                    metadata = await self.image_store.get_image_metadata(result["vector_id"])
                    if metadata:
                        result["image_metadata"] = metadata
                
                enriched_results.append(result)
            
            return enriched_results
            
        except Exception as e:
            logger.error(f"Text search failed: {e}")
            return []
    
    async def search_by_image(self, image_gcs_uri: str, top_k: int = 10) -> List[Dict]:
        """Search using image query"""
        try:
            logger.info(f"Image search: uri={image_gcs_uri}, top_k={top_k}")
            
            # Generate query embedding
            query_embedding = await self.embedder.embed_image(image_gcs_uri=image_gcs_uri)
            
            # Search vectors
            results = await self.vector_store.search(
                query_embedding=query_embedding,
                top_k=top_k
            )
            
            # Enrich with metadata
            enriched_results = []
            for result in results:
                if result["vector_type"] == "image":
                    metadata = await self.image_store.get_image_metadata(result["vector_id"])
                    if metadata:
                        result["image_metadata"] = metadata
                
                enriched_results.append(result)
            
            return enriched_results
            
        except Exception as e:
            logger.error(f"Image search failed: {e}")
            return []
    
    async def index_image(
        self, 
        file_content: bytes, 
        filename: str,
        description: str = None,
        tags: List[str] = None
    ) -> Dict:
        """
        Upload and index an image.
        
        Returns:
            Dict with image_id, gcs_uri, public_url
        """
        try:
            logger.info(f"Indexing image: {filename}")
            
            # Upload image
            upload_result = await self.image_store.upload_image(
                file_content=file_content,
                filename=filename,
                metadata={
                    "description": description,
                    "tags": tags or []
                }
            )
            
            image_id = upload_result["image_id"]
            gcs_uri = upload_result["gcs_uri"]
            
            # Generate embedding
            embedding = await self.embedder.embed_image(image_gcs_uri=gcs_uri)
            
            # Store vector
            await self.vector_store.add_vector(
                vector_id=image_id,
                embedding=embedding,
                vector_type="image",
                metadata={
                    "filename": filename,
                    "description": description,
                    "tags": tags or [],
                    "gcs_uri": gcs_uri
                }
            )
            
            logger.info(f"Image indexed successfully: {image_id}")
            return upload_result
            
        except Exception as e:
            logger.error(f"Image indexing failed: {e}")
            raise
    
    async def delete_image(self, image_id: str):
        """Delete image and its vector"""
        try:
            # Delete vector
            await self.vector_store.delete_vector(image_id)
            
            # Delete image
            await self.image_store.delete_image(image_id)
            
            logger.info(f"Image and vector deleted: {image_id}")
            
        except Exception as e:
            logger.error(f"Image deletion failed: {e}")
            raise
