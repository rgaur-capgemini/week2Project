"""
Week 5 - Agentic AI Agent using Google ADK + Vertex AI + Gemini LLM.

Architecture:
    User Query
        ↓
    RAGAgent (Google ADK)
        ↓ selects tool
    ┌──────────────┬───────────────┬──────────────┐
    │ rag_search   │ csv_analyze   │ multimodal   │
    │ (Vertex AI)  │ (GCS/Pandas)  │ (Gemini Vis) │
    └──────────────┴───────────────┴──────────────┘
        ↓ aggregates results
    Gemini LLM (Final Answer Generation)
"""

import os
import time
import json
import logging
from typing import Any, Dict, List, Optional

import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    Tool,
    FunctionDeclaration,
    Content,
    Part,
    GenerationConfig,
)

from week5.agentic_ai.tools import AgentToolkit

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Tool function declarations for Gemini
# ──────────────────────────────────────────────

SEARCH_DOCUMENTS_FUNC = FunctionDeclaration(
    name="search_documents",
    description=(
        "Search the RAG knowledge base for relevant document chunks "
        "that help answer the user's question. Use this tool when the "
        "user asks about information that may be in ingested documents."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query derived from the user question.",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of top chunks to retrieve (default: 5).",
            },
        },
        "required": ["query"],
    },
)

ANALYZE_CSV_FUNC = FunctionDeclaration(
    name="analyze_csv",
    description=(
        "Analyze a CSV file stored in GCS. Provides statistics, "
        "column info, data samples, and answers data-related questions. "
        "Use this tool when the user asks questions about tabular data or CSV files."
    ),
    parameters={
        "type": "object",
        "properties": {
            "gcs_uri": {
                "type": "string",
                "description": "GCS URI of the CSV file, e.g. gs://bucket/file.csv",
            },
            "question": {
                "type": "string",
                "description": "Specific question to answer about the CSV data.",
            },
            "operation": {
                "type": "string",
                "enum": ["summary", "filter", "aggregate", "sample"],
                "description": "Type of analysis to perform on the CSV.",
            },
        },
        "required": ["gcs_uri", "question"],
    },
)

SUMMARIZE_DOCUMENT_FUNC = FunctionDeclaration(
    name="summarize_document",
    description=(
        "Fetch and summarize a document from GCS. "
        "Use this tool when the user wants a summary of a specific document."
    ),
    parameters={
        "type": "object",
        "properties": {
            "gcs_uri": {
                "type": "string",
                "description": "GCS URI of the document to summarize.",
            },
            "focus": {
                "type": "string",
                "description": "Specific aspect to focus the summary on (optional).",
            },
        },
        "required": ["gcs_uri"],
    },
)

PROCESS_IMAGE_FUNC = FunctionDeclaration(
    name="process_image",
    description=(
        "Analyze an image using Gemini Vision. Extracts text (OCR), "
        "describes visual content, and answers questions about the image. "
        "Use this when the user uploads or references an image."
    ),
    parameters={
        "type": "object",
        "properties": {
            "image_uri": {
                "type": "string",
                "description": "GCS URI or base64 data URI of the image.",
            },
            "question": {
                "type": "string",
                "description": "Question to answer about the image.",
            },
        },
        "required": ["image_uri", "question"],
    },
)

GET_COST_SUMMARY_FUNC = FunctionDeclaration(
    name="get_cost_summary",
    description=(
        "Retrieve GCP cost and token usage summary for FinOps reporting. "
        "Use this when the user asks about costs, budget, or token consumption."
    ),
    parameters={
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Number of past days to summarize costs for (default: 30).",
            }
        },
        "required": [],
    },
)


class RAGAgent:
    """
    Agentic AI system powered by Google ADK concepts + Vertex AI + Gemini.

    The agent uses Gemini's function-calling capability to decide which
    tools to invoke, then synthesises a final answer from tool outputs.
    """

    SYSTEM_PROMPT = """You are an intelligent AI assistant with access to a set of tools.
Your goal is to answer user questions accurately by using the most relevant tool(s).

Available tools:
- search_documents: Search the RAG knowledge base for relevant content.
- analyze_csv: Analyze CSV/tabular data stored in GCS.
- summarize_document: Fetch and summarize a GCS document.
- process_image: Analyze images using Gemini Vision.
- get_cost_summary: Get GCP cost and token usage summary.

Guidelines:
1. Always select the best tool(s) for the question.
2. Chain multiple tool calls when needed to get a complete answer.
3. Cite the sources or data used in your final answer.
4. If no tool is needed, answer directly from your knowledge.
5. Be concise, accurate, and structured in your responses.
"""

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model_name: str = "gemini-2.0-flash-001",
        max_tool_calls: int = 5,
    ):
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self.max_tool_calls = max_tool_calls

        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)

        # Build tool kit
        self.toolkit = AgentToolkit(project_id=project_id, location=location)

        # Register Gemini tools
        self._gemini_tools = Tool(
            function_declarations=[
                SEARCH_DOCUMENTS_FUNC,
                ANALYZE_CSV_FUNC,
                SUMMARIZE_DOCUMENT_FUNC,
                PROCESS_IMAGE_FUNC,
                GET_COST_SUMMARY_FUNC,
            ]
        )

        # Instantiate Gemini model
        self.model = GenerativeModel(
            model_name=model_name,
            tools=[self._gemini_tools],
            system_instruction=self.SYSTEM_PROMPT,
        )

        self._generation_config = GenerationConfig(
            temperature=0.2,
            max_output_tokens=4096,
            top_p=0.95,
        )

        logger.info(
            f"RAGAgent initialized | model={model_name} | project={project_id}"
        )

    # ──────────────────────────────────────────────
    # Tool dispatcher
    # ──────────────────────────────────────────────

    def _dispatch_tool(self, function_call) -> str:
        """Route a Gemini function call to the correct toolkit method."""
        name = function_call.name
        args: dict = dict(function_call.args)

        logger.info(f"Agent dispatching tool: {name} | args={args}")

        try:
            if name == "search_documents":
                result = self.toolkit.search_documents(
                    query=args["query"],
                    top_k=int(args.get("top_k", 5)),
                )
            elif name == "analyze_csv":
                result = self.toolkit.analyze_csv(
                    gcs_uri=args["gcs_uri"],
                    question=args["question"],
                    operation=args.get("operation", "summary"),
                )
            elif name == "summarize_document":
                result = self.toolkit.summarize_document(
                    gcs_uri=args["gcs_uri"],
                    focus=args.get("focus"),
                )
            elif name == "process_image":
                result = self.toolkit.process_image(
                    image_uri=args["image_uri"],
                    question=args["question"],
                )
            elif name == "get_cost_summary":
                result = self.toolkit.get_cost_summary(
                    days=int(args.get("days", 30))
                )
            else:
                result = {"error": f"Unknown tool: {name}"}

            return json.dumps(result, default=str)

        except Exception as exc:
            logger.error(f"Tool '{name}' failed: {exc}")
            return json.dumps({"error": str(exc)})

    # ──────────────────────────────────────────────
    # Main agentic loop
    # ──────────────────────────────────────────────

    def run(
        self,
        user_query: str,
        session_id: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the agentic loop for a user query.

        Args:
            user_query: The user's question or instruction.
            session_id: Optional session identifier.
            conversation_history: Prior conversation turns (role/content dicts).

        Returns:
            Dict containing 'answer', 'tool_calls', 'sources', and 'latency_ms'.
        """
        start_time = time.time()
        tool_calls_log: List[Dict] = []
        sources: List[str] = []

        # Build message history
        messages: List[Content] = []
        if conversation_history:
            for turn in conversation_history:
                role = "user" if turn.get("role") == "user" else "model"
                messages.append(
                    Content(role=role, parts=[Part.from_text(turn["content"])])
                )

        # Add current user query
        messages.append(Content(role="user", parts=[Part.from_text(user_query)]))

        # Agentic loop
        chat = self.model.start_chat(history=messages[:-1])
        response = chat.send_message(
            user_query,
            generation_config=self._generation_config,
        )

        tool_call_count = 0

        while tool_call_count < self.max_tool_calls:
            # Check for function calls in the response
            function_calls = []
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if part.function_call and part.function_call.name:
                        function_calls.append(part.function_call)

            if not function_calls:
                break  # No more tool calls – we have a final answer

            # Execute all function calls in this response
            tool_responses = []
            for fc in function_calls:
                tool_result = self._dispatch_tool(fc)
                result_data = json.loads(tool_result)

                tool_calls_log.append(
                    {
                        "tool": fc.name,
                        "args": dict(fc.args),
                        "result_preview": tool_result[:200],
                    }
                )

                # Collect source references
                if "sources" in result_data:
                    sources.extend(result_data["sources"])
                elif "gcs_uri" in dict(fc.args):
                    sources.append(dict(fc.args)["gcs_uri"])

                tool_responses.append(
                    Part.from_function_response(
                        name=fc.name,
                        response={"content": tool_result},
                    )
                )

            # Send tool results back to model
            response = chat.send_message(
                Content(role="tool", parts=tool_responses),
                generation_config=self._generation_config,
            )
            tool_call_count += 1

        # Extract final text answer
        final_answer = ""
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "text") and part.text:
                    final_answer += part.text

        latency_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Agent completed | session={session_id} | "
            f"tool_calls={tool_call_count} | latency_ms={latency_ms}"
        )

        return {
            "answer": final_answer,
            "tool_calls": tool_calls_log,
            "sources": list(set(sources)),
            "latency_ms": latency_ms,
            "session_id": session_id,
            "model": self.model_name,
        }
