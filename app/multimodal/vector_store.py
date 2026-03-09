"""
Multimodal Vector Store - Week 5
Store and search multimodal embeddings.
"""

from typing import List, Dict
from google.cloud import firestore
from datetime import datetime
import numpy as np
from app.logging_config import get_logger

logger = get_logger(__name__)


class MultiModalVectorStore:
    """Store and search 1408-dim multimodal embeddings"""
    
    def __init__(self):
        self.db = firestore.Client()
        self.collection = "multimodal_vectors"
        self.dimension = 1408
        logger.info(f"Multimodal vector store initialized (dim={self.dimension})")
    
    async def add_vector(
        self, 
        vector_id: str, 
        embedding: List[float], 
        vector_type: str,
        metadata: Dict = None
    ):
        """
        Add vector to store.
        
        Args:
            vector_id: Unique ID (e.g., image_id or text_id)
            embedding: 1408-dim embedding
            vector_type: "image", "text", or "multimodal"
            metadata: Additional metadata
        """
        try:
            if len(embedding) != self.dimension:
                raise ValueError(f"Expected {self.dimension}-dim vector, got {len(embedding)}")
            
            doc_ref = self.db.collection(self.collection).document(vector_id)
            doc_ref.set({
                "vector_id": vector_id,
                "embedding": embedding,
                "vector_type": vector_type,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Vector added: {vector_id} (type={vector_type})")
            
        except Exception as e:
            logger.error(f"Add vector failed: {e}")
            raise
    
    async def search(
        self, 
        query_embedding: List[float], 
        top_k: int = 10,
        vector_type: str = None
    ) -> List[Dict]:
        """
        Search for similar vectors using cosine similarity.
        
        Note: This is a simple implementation. For production,
        use Vertex AI Vector Search or similar service.
        """
        try:
            if len(query_embedding) != self.dimension:
                raise ValueError(f"Expected {self.dimension}-dim vector, got {len(query_embedding)}")
            
            # Get all vectors (filter by type if specified)
            query = self.db.collection(self.collection)
            if vector_type:
                query = query.where("vector_type", "==", vector_type)
            
            docs = query.stream()
            
            # Calculate cosine similarity
            results = []
            query_vec = np.array(query_embedding)
            query_norm = np.linalg.norm(query_vec)
            
            for doc in docs:
                data = doc.to_dict()
                doc_vec = np.array(data["embedding"])
                doc_norm = np.linalg.norm(doc_vec)
                
                if query_norm > 0 and doc_norm > 0:
                    similarity = np.dot(query_vec, doc_vec) / (query_norm * doc_norm)
                    results.append({
                        "vector_id": data["vector_id"],
                        "similarity": float(similarity),
                        "vector_type": data["vector_type"],
                        "metadata": data["metadata"]
                    })
            
            # Sort by similarity
            results.sort(key=lambda x: x["similarity"], reverse=True)
            
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def delete_vector(self, vector_id: str):
        """Delete vector from store"""
        try:
            doc_ref = self.db.collection(self.collection).document(vector_id)
            doc_ref.delete()
            logger.info(f"Vector deleted: {vector_id}")
            
        except Exception as e:
            logger.error(f"Delete vector failed: {e}")
            raise
