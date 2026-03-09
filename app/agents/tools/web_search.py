"""
Web Search Tool - Week 5
Search the internet using Google Custom Search API.
"""

from typing import List
import httpx
import os
from app.agents.tools.base import BaseTool, ToolParameter, ToolResult
from app.logging_config import get_logger

logger = get_logger(__name__)


class WebSearchTool(BaseTool):
    """Search the web using Google Custom Search"""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        self.engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        logger.info(f"Web search tool initialized (API configured: {bool(self.api_key)})")
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return "Search the internet for current information using Google Custom Search"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="Search query",
                required=True
            ),
            ToolParameter(
                name="num_results",
                type="number",
                description="Number of results to return (max 10, default 5)",
                required=False,
                default=5
            )
        ]
    
    async def execute(self, query: str, num_results: int = 5, **kwargs) -> ToolResult:
        try:
            logger.info(f"Web search: query='{query}', num={num_results}")
            
            # Check if API is configured
            if not self.api_key or not self.engine_id:
                return ToolResult(
                    success=False,
                    error="Google Custom Search API not configured. Set GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID environment variables."
                )
            
            # Google Custom Search API endpoint
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.api_key,
                "cx": self.engine_id,
                "q": query,
                "num": min(num_results, 10)
            }
            
            # Make request
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
            
            # Extract results
            items = data.get("items", [])
            results = []
            for item in items:
                results.append({
                    "title": item.get("title"),
                    "snippet": item.get("snippet"),
                    "link": item.get("link"),
                    "displayLink": item.get("displayLink")
                })
            
            return ToolResult(
                success=True,
                data={"results": results, "count": len(results)},
                metadata={"query": query}
            )
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return ToolResult(success=False, error=str(e))
