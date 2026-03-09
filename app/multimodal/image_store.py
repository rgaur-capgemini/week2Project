"""
Image Storage - Week 5
Store images in GCS with metadata in Firestore.
"""

from google.cloud import storage, firestore
from datetime import datetime
from typing import Dict, Optional
import uuid
from app.logging_config import get_logger

logger = get_logger(__name__)


class ImageStore:
    """Store images in GCS with Firestore metadata"""
    
    def __init__(self):
        self.storage_client = storage.Client()
        self.bucket_name = "botpproject-images"
        self.bucket = self.storage_client.bucket(self.bucket_name)
        
        self.db = firestore.Client()
        self.collection = "image_metadata"
        
        logger.info(f"Image store initialized (bucket={self.bucket_name})")
    
    async def upload_image(
        self, 
        file_content: bytes, 
        filename: str,
        content_type: str = "image/jpeg",
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Upload image to GCS and store metadata in Firestore.
        
        Returns:
            Dict with image_id, gcs_uri, public_url
        """
        try:
            # Generate unique ID
            image_id = str(uuid.uuid4())
            blob_path = f"images/{image_id}/{filename}"
            
            # Upload to GCS
            blob = self.bucket.blob(blob_path)
            blob.upload_from_string(file_content, content_type=content_type)
            
            gcs_uri = f"gs://{self.bucket_name}/{blob_path}"
            public_url = blob.public_url
            
            # Store metadata in Firestore
            doc_ref = self.db.collection(self.collection).document(image_id)
            doc_ref.set({
                "image_id": image_id,
                "filename": filename,
                "gcs_uri": gcs_uri,
                "blob_path": blob_path,
                "public_url": public_url,
                "content_type": content_type,
                "size_bytes": len(file_content),
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Image uploaded: {image_id}")
            
            return {
                "image_id": image_id,
                "gcs_uri": gcs_uri,
                "public_url": public_url,
                "filename": filename
            }
            
        except Exception as e:
            logger.error(f"Image upload failed: {e}")
            raise
    
    async def get_image_metadata(self, image_id: str) -> Optional[Dict]:
        """Get image metadata from Firestore"""
        try:
            doc_ref = self.db.collection(self.collection).document(image_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"Get metadata failed: {e}")
            return None
    
    async def delete_image(self, image_id: str):
        """Delete image from GCS and Firestore"""
        try:
            # Get metadata
            metadata = await self.get_image_metadata(image_id)
            if not metadata:
                raise ValueError(f"Image {image_id} not found")
            
            # Delete from GCS
            blob_path = metadata["blob_path"]
            blob = self.bucket.blob(blob_path)
            blob.delete()
            
            # Delete from Firestore
            doc_ref = self.db.collection(self.collection).document(image_id)
            doc_ref.delete()
            
            logger.info(f"Image deleted: {image_id}")
            
        except Exception as e:
            logger.error(f"Image deletion failed: {e}")
            raise
    
    async def list_images(self, limit: int = 50) -> list:
        """List recent images"""
        try:
            images = []
            query = (
                self.db.collection(self.collection)
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )
            
            for doc in query.stream():
                images.append(doc.to_dict())
            
            return images
            
        except Exception as e:
            logger.error(f"List images failed: {e}")
            return []
