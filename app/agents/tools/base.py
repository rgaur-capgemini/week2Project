"""
Base Tool Interface - Week 5
Abstract base class for all agent tools with Vertex AI function calling support.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Tool parameter definition"""
    name: str
    type: str  # string, number, boolean, object, array
    description: str
    required: bool = False
    enum: Optional[List[str]] = None
    default: Optional[Any] = None


class ToolResult(BaseModel):
    """Standard tool execution result"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseTool(ABC):
    """
    Abstract base class for agent tools.
    All tools must implement name, description, parameters, and execute methods.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return tool name (used for function calling)"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return tool description for LLM"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """Return list of tool parameters"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            ToolResult with success status and data/error
        """
        pass
    
    def to_function_declaration(self) -> Dict[str, Any]:
        """
        Convert tool to Vertex AI function declaration format.
        
        Returns:
            Dictionary compatible with Gemini function calling
        """
        # Build parameters schema
        properties = {}
        required_params = []
        
        for param in self.parameters:
            param_schema = {
                "type": param.type,
                "description": param.description
            }
            
            if param.enum:
                param_schema["enum"] = param.enum
            
            if param.default is not None:
                param_schema["default"] = param.default
            
            properties[param.name] = param_schema
            
            if param.required:
                required_params.append(param.name)
        
        parameters_schema = {
            "type": "object",
            "properties": properties
        }
        
        if required_params:
            parameters_schema["required"] = required_params
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": parameters_schema
        }
    
    def validate_parameters(self, **kwargs) -> bool:
        """
        Validate that all required parameters are provided.
        
        Args:
            **kwargs: Provided parameters
            
        Returns:
            True if valid, raises ValueError otherwise
        """
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                raise ValueError(f"Missing required parameter: {param.name}")
        
        return True
