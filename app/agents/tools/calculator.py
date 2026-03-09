"""
Calculator Tool - Week 5
Safe mathematical calculations using AST parsing (no eval).
"""

import ast
import operator
from typing import List
from app.agents.tools.base import BaseTool, ToolParameter, ToolResult
from app.logging_config import get_logger

logger = get_logger(__name__)


class CalculatorTool(BaseTool):
    """Safe calculator using AST (no eval)"""
    
    # Allowed operations
    ALLOWED_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return "Perform mathematical calculations. Supports +, -, *, /, ** (power). Example: '25 * 4' or '(10 + 5) ** 2'"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="expression",
                type="string",
                description="Mathematical expression to evaluate",
                required=True
            )
        ]
    
    def _safe_eval(self, node):
        """Recursively evaluate AST node"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            op = type(node.op)
            if op not in self.ALLOWED_OPS:
                raise ValueError(f"Operation not allowed: {op.__name__}")
            left = self._safe_eval(node.left)
            right = self._safe_eval(node.right)
            return self.ALLOWED_OPS[op](left, right)
        elif isinstance(node, ast.UnaryOp):
            op = type(node.op)
            if op not in self.ALLOWED_OPS:
                raise ValueError(f"Operation not allowed: {op.__name__}")
            operand = self._safe_eval(node.operand)
            return self.ALLOWED_OPS[op](operand)
        else:
            raise ValueError(f"Invalid expression node: {type(node).__name__}")
    
    async def execute(self, expression: str, **kwargs) -> ToolResult:
        try:
            logger.info(f"Calculator: expression='{expression}'")
            
            # Parse expression into AST
            tree = ast.parse(expression, mode='eval')
            
            # Evaluate safely
            result = self._safe_eval(tree.body)
            
            return ToolResult(
                success=True,
                data={"result": result, "expression": expression},
                metadata={"type": type(result).__name__}
            )
            
        except ZeroDivisionError:
            return ToolResult(success=False, error="Division by zero")
        except SyntaxError as e:
            return ToolResult(success=False, error=f"Invalid syntax: {e}")
        except Exception as e:
            logger.error(f"Calculator error: {e}")
            return ToolResult(success=False, error=str(e))
