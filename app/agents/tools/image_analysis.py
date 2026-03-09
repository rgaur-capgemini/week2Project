"""
Image Analysis Tool - Week 5
Analyze images using Gemini Vision.
"""

from typing import List
from vertexai.generative_models import GenerativeModel, Part
from app.agents.tools.base import BaseTool, ToolParameter, ToolResult
from app.logging_config import get_logger

logger = get_logger(__name__)


class ImageAnalysisTool(BaseTool):
    """Analyze images with Gemini Vision"""
    
    def __init__(self):
        self.model = GenerativeModel("gemini-2.0-flash-001")
        logger.info("Image analysis tool initialized")
    
    @property
    def name(self) -> str:
        return "image_analysis"
    
    @property
    def description(self) -> str:
        return "Analyze images and answer questions about them using Gemini Vision. Supports GCS URIs (gs://) and public URLs."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="image_uri",
                type="string",
                description="Image URI (gs://bucket/path or https://...)",
                required=True
            ),
            ToolParameter(
                name="question",
                type="string",
                description="Specific question about the image (optional)",
                required=False
            ),
            ToolParameter(
                name="detail_level",
                type="string",
                description="Detail level: brief, normal, or detailed",
                required=False,
                enum=["brief", "normal", "detailed"],
                default="normal"
            )
        ]
    
    async def execute(self, image_uri: str, question: str = None, detail_level: str = "normal", **kwargs) -> ToolResult:
        try:
            logger.info(f"Image analysis: uri={image_uri}, question='{question}'")
            
            # Build prompt based on detail level
            if question:
                prompt = question
            else:
                prompts = {
                    "brief": "Describe this image briefly in 1-2 sentences.",
                    "normal": "Describe this image in detail. What do you see?",
                    "detailed": "Provide a comprehensive analysis of this image, including objects, text, layout, colors, and any notable features."
                }
                prompt = prompts.get(detail_level, prompts["normal"])
            
            # Load image
            image_part = Part.from_uri(image_uri, mime_type="image/jpeg")
            
            # Generate response
            response = self.model.generate_content([prompt, image_part])
            
            return ToolResult(
                success=True,
                data={"analysis": response.text, "image_uri": image_uri},
                metadata={"question": question, "detail_level": detail_level}
            )
            
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return ToolResult(success=False, error=str(e))
