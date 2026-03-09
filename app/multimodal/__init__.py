"""
Multimodal AI Components - Week 5
Text and image processing with unified embeddings.
"""

from app.multimodal.embeddings import MultiModalEmbedder
from app.multimodal.image_store import ImageStore
from app.multimodal.vector_store import MultiModalVectorStore
from app.multimodal.retriever import MultiModalRetriever

__all__ = ["MultiModalEmbedder", "ImageStore", "MultiModalVectorStore", "MultiModalRetriever"]
