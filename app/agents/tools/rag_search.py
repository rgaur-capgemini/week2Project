"""
RAG Search Tool - Week 5
Search knowledge base using existing RAG system components.
"""

from typing import List
from app.agents.tools.base import BaseTool, ToolParameter, ToolResult
from app.rag.embeddings import VertexTextEmbedder
from app.rag.vector_store import VertexVectorStore
from app.storage.firestore_store import FirestoreChunkStore
from app.logging_config import get_logger

logger = get_logger(__name__)


class RAGSearchTool(BaseTool):
    """Search knowledge base using semantic similarity"""
    
    def __init__(self):
        try:
            self.embedder = VertexTextEmbedder()
            self.vector_store = VertexVectorStore()
            self.chunk_store = FirestoreChunkStore()
            logger.info("RAG search tool initialized")
        except Exception as e:
            logger.error(f"RAG search tool init failed: {e}")
            raise
    
    @property
    def name(self) -> str:
        return "rag_search"
    
    @property
    def description(self) -> str:
        return "Search the knowledge base for relevant documents and information using semantic similarity"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="Search query or question",
                required=True
            ),
            ToolParameter(
                name="top_k",
                type="number",
                description="Number of results to return (default 5)",
                required=False,
                default=5
            )
        ]
    
    async def execute(self, query: str, top_k: int = 5, **kwargs) -> ToolResult:
        try:
            logger.info(f"RAG search: query='{query}', top_k={top_k}")
            
            # Generate query embedding
            query_embedding = await self.embedder.embed(query)
            
            # Search vector store
            results = await self.vector_store.search(
                query_embedding=query_embedding,
                top_k=top_k
            )
            
            if not results:
                return ToolResult(
                    success=True,
                    data={"results": [], "message": "No relevant documents found"},
                    metadata={"query": query, "count": 0}
                )
            
            # Get chunk details from Firestore
            formatted_results = []
            for i, result in enumerate(results, 1):
                chunk_id = result.get("chunk_id")
                similarity = result.get("similarity", 0.0)
                
                # Try to get chunk content
                chunk_data = {}
                try:
                    chunk = await self.chunk_store.get_chunk(chunk_id)
                    if chunk:
                        chunk_data = {
                            "content": chunk.get("text", ""),
                            "source": chunk.get("document_id", "Unknown"),
                            "metadata": chunk.get("metadata", {})
                        }
                except:
                    chunk_data = {"content": "Content not available", "source": "Unknown"}
                
                formatted_results.append({
                    "rank": i,
                    "similarity": round(similarity, 3),
                    **chunk_data
                })
            
            return ToolResult(
                success=True,
                data={"results": formatted_results},
                metadata={"query": query, "count": len(formatted_results)}
            )
            
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )
