"""
Agent Orchestrator - Week 5
Coordinate agent tools using Gemini 2.0 Flash with function calling.
"""

from typing import List, Dict, Any, Optional
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration, Part
import json
from app.agents.memory import AgentMemory
from app.agents.tools import (
    RAGSearchTool, CalculatorTool, CSVQueryTool, 
    ImageAnalysisTool, WebSearchTool
)
from app.logging_config import get_logger

logger = get_logger(__name__)


class AgentOrchestrator:
    """Coordinate tool execution using Gemini function calling"""
    
    def __init__(self):
        self.model = GenerativeModel("gemini-2.0-flash-001")
        self.memory = AgentMemory()
        
        # Initialize tools
        self.tools = {
            "rag_search": RAGSearchTool(),
            "calculator": CalculatorTool(),
            "csv_query": CSVQueryTool(),
            "image_analysis": ImageAnalysisTool(),
            "web_search": WebSearchTool()
        }
        
        # Build function declarations for Vertex AI
        self.function_declarations = self._build_function_declarations()
        self.vertex_tools = [Tool(function_declarations=self.function_declarations)]
        
        logger.info(f"Agent orchestrator initialized with {len(self.tools)} tools")
    
    def _build_function_declarations(self) -> List[FunctionDeclaration]:
        """Convert tools to Vertex AI function declarations"""
        declarations = []
        for tool in self.tools.values():
            decl_dict = tool.to_function_declaration()
            declarations.append(FunctionDeclaration(
                name=decl_dict["name"],
                description=decl_dict["description"],
                parameters=decl_dict["parameters"]
            ))
        return declarations
    
    async def chat(
        self, 
        message: str, 
        session_id: str, 
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Process user message with agentic reasoning loop.
        
        Args:
            message: User message
            session_id: Conversation session ID
            max_iterations: Maximum tool call iterations
        
        Returns:
            Response with agent's answer and execution trace
        """
        try:
            logger.info(f"Agent chat: session={session_id}, message='{message[:100]}'")
            
            # Add user message to memory
            await self.memory.add_message(session_id, "user", message)
            
            # Get conversation history
            history = await self.memory.get_history(session_id, limit=10)
            
            # Build conversation context
            conversation = []
            for msg in history[:-1]:  # Exclude current message
                conversation.append({
                    "role": msg["role"],
                    "parts": [msg["content"]]
                })
            
            # Add current message
            conversation.append({
                "role": "user",
                "parts": [message]
            })
            
            # Agentic reasoning loop
            execution_trace = []
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                logger.info(f"Agent iteration {iteration}/{max_iterations}")
                
                # Generate response with tools
                chat = self.model.start_chat()
                response = chat.send_message(
                    conversation[-1]["parts"][0],
                    tools=self.vertex_tools
                )
                
                # Check if function call is requested
                function_calls = []
                if response.candidates:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            function_calls.append(part.function_call)
                
                # If no function calls, we have final answer
                if not function_calls:
                    final_answer = response.text
                    logger.info("Agent reached final answer")
                    
                    # Add assistant response to memory
                    await self.memory.add_message(
                        session_id, 
                        "assistant", 
                        final_answer,
                        metadata={"iterations": iteration, "tool_calls": len(execution_trace)}
                    )
                    
                    return {
                        "answer": final_answer,
                        "session_id": session_id,
                        "iterations": iteration,
                        "execution_trace": execution_trace
                    }
                
                # Execute function calls
                for fc in function_calls:
                    tool_name = fc.name
                    tool_args = dict(fc.args.items())
                    
                    logger.info(f"Executing tool: {tool_name} with args {tool_args}")
                    
                    # Execute tool
                    if tool_name in self.tools:
                        result = await self.tools[tool_name].execute(**tool_args)
                        
                        execution_trace.append({
                            "iteration": iteration,
                            "tool": tool_name,
                            "args": tool_args,
                            "success": result.success,
                            "result": result.data if result.success else result.error
                        })
                        
                        # Add function response to conversation
                        conversation.append({
                            "role": "function",
                            "parts": [json.dumps({
                                "name": tool_name,
                                "response": result.data if result.success else {"error": result.error}
                            })]
                        })
                    else:
                        logger.warning(f"Unknown tool requested: {tool_name}")
                        execution_trace.append({
                            "iteration": iteration,
                            "tool": tool_name,
                            "args": tool_args,
                            "success": False,
                            "result": f"Tool '{tool_name}' not found"
                        })
            
            # Max iterations reached
            logger.warning(f"Agent reached max iterations ({max_iterations})")
            return {
                "answer": "I've performed several tool operations but need more iterations to complete. Please refine your request.",
                "session_id": session_id,
                "iterations": iteration,
                "execution_trace": execution_trace,
                "warning": "Max iterations reached"
            }
            
        except Exception as e:
            logger.error(f"Agent chat failed: {e}")
            raise
    
    def get_available_tools(self) -> List[Dict[str, str]]:
        """Get list of available tools"""
        return [
            {
                "name": tool.name,
                "description": tool.description
            }
            for tool in self.tools.values()
        ]
