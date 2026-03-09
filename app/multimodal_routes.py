"""
Multimodal API Routes - Week 5
FastAPI endpoints for multimodal image processing.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from app.multimodal import MultiModalRetriever
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/multimodal", tags=["multimodal"])

# Lazy initialization to avoid GCP credential errors at import time
_retriever = None

def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = MultiModalRetriever()
    return _retriever


class SearchTextRequest(BaseModel):
    """Text search request"""
    query: str = Field(..., description="Search query")
    top_k: Optional[int] = Field(10, description="Number of results", ge=1, le=50)
    vector_type: Optional[str] = Field(None, description="Filter by type: image, text, or multimodal")


class SearchImageRequest(BaseModel):
    """Image search request"""
    image_gcs_uri: str = Field(..., description="GCS URI of query image (gs://...)")
    top_k: Optional[int] = Field(10, description="Number of results", ge=1, le=50)


class UploadResponse(BaseModel):
    """Image upload response"""
    image_id: str
    gcs_uri: str
    public_url: str
    filename: str
    message: str


@router.post("/images/upload", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None)
):
    """
    Upload and index an image for multimodal search.
    
    The image will be:
    1. Stored in GCS
    2. Embedded using multimodalembedding@001
    3. Indexed for vector search
    """
    try:
        logger.info(f"Image upload: {file.filename}")
        
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file content
        content = await file.read()
        
        # Parse tags
        tag_list = [t.strip() for t in tags.split(",")] if tags else []
        
        # Upload and index
        retriever = get_retriever()
        result = await retriever.index_image(
            file_content=content,
            filename=file.filename,
            description=description,
            tags=tag_list
        )
        
        return UploadResponse(
            **result,
            message="Image uploaded and indexed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/text")
async def search_by_text(request: SearchTextRequest):
    """
    Search images and content using text query.
    
    Uses multimodal embeddings to find visually and semantically similar content.
    """
    try:
        logger.info(f"Text search: query='{request.query}'")
        
        retriever = get_retriever()
        results = await retriever.search_by_text(
            query=request.query,
            top_k=request.top_k,
            vector_type=request.vector_type
        )
        
        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Text search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/image")
async def search_by_image(request: SearchImageRequest):
    """
    Search for similar images using an image query.
    
    Provide a GCS URI of an uploaded image to find visually similar images.
    """
    try:
        logger.info(f"Image search: uri={request.image_gcs_uri}")
        
        retriever = get_retriever()
        results = await retriever.search_by_image(
            image_gcs_uri=request.image_gcs_uri,
            top_k=request.top_k
        )
        
        return {
            "query_image": request.image_gcs_uri,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Image search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/images/{image_id}")
async def delete_image(image_id: str):
    """Delete an image and its vector embedding"""
    try:
        logger.info(f"Delete image: {image_id}")
        
        retriever = get_retriever()
        await retriever.delete_image(image_id)
        
        return {"message": f"Image {image_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Image deletion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/images")
async def list_images(limit: int = 50):
    """List recently uploaded images"""
    try:
        retriever = get_retriever()
        images = await retriever.image_store.list_images(limit=limit)
        return {"images": images, "count": len(images)}
        
    except Exception as e:
        logger.error(f"List images failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
