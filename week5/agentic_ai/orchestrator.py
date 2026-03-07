"""
Week 5 - Multi-Agent Orchestrator.

Routes incoming requests to the appropriate specialised agent:
    - RAGAgent        : document Q&A, knowledge retrieval
    - CSVAgent        : tabular / CSV data analysis
    - MultimodalAgent : image + text combined tasks
    - FinOpsAgent     : cost and usage analysis

The orchestrator itself uses Gemini to decide which agent(s) to invoke.
"""

import logging
import time
from typing import Any, Dict, List, Optional

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

from week5.agentic_ai.agent import RAGAgent

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Intent classifier prompt
# ──────────────────────────────────────────────────────────────────────────────
INTENT_CLASSIFIER_PROMPT = """You are an intent classifier for an AI assistant.
Given the user query, classify it into ONE of these categories:
- rag: questions about documents, knowledge base, or general Q&A
- csv: questions about tabular data, spreadsheets, or CSV files
- multimodal: requests involving images, charts, or visual content
- finops: questions about costs, billing, token usage, or budget
- general: everything else

Respond with ONLY the category name (lowercase). No explanation needed.

User query: {query}
"""


class MultiAgentOrchestrator:
    """
    Routes queries to the correct specialised agent and merges results
    when multiple agents are needed.
    """

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model_name: str = "gemini-2.0-flash-001",
    ):
        self.project_id = project_id
        self.location = location
        self.model_name = model_name

        vertexai.init(project=project_id, location=location)

        # Shared RAGAgent handles most specialised use-cases through tool dispatch
        self._rag_agent = RAGAgent(
            project_id=project_id,
            location=location,
            model_name=model_name,
        )

        # Classifier model (no tools needed)
        self._classifier = GenerativeModel(model_name)
        self._gen_config = GenerationConfig(temperature=0.0, max_output_tokens=10)

        logger.info(f"MultiAgentOrchestrator ready | project={project_id}")

    # ──────────────────────────────────────────────
    # Intent detection
    # ──────────────────────────────────────────────

    def _classify_intent(self, query: str) -> str:
        """Use Gemini to classify the query intent."""
        try:
            prompt = INTENT_CLASSIFIER_PROMPT.format(query=query)
            response = self._classifier.generate_content(
                prompt, generation_config=self._gen_config
            )
            intent = response.text.strip().lower()
            if intent not in {"rag", "csv", "multimodal", "finops", "general"}:
                intent = "rag"  # safe default
            return intent
        except Exception:
            return "rag"

    # ──────────────────────────────────────────────
    # Route and execute
    # ──────────────────────────────────────────────

    def run(
        self,
        user_query: str,
        session_id: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Classify intent and route to the appropriate agent.

        Args:
            user_query: The user's question.
            session_id: Session tracking ID.
            conversation_history: Prior conversation turns.
            metadata: Extra context (e.g., gcs_uri, image_uri).

        Returns:
            Standardised result dict with 'answer', 'intent', 'agent_used', etc.
        """
        start = time.time()
        metadata = metadata or {}

        intent = self._classify_intent(user_query)
        logger.info(f"Orchestrator intent={intent} | session={session_id}")

        # Augment query with metadata context when available
        augmented_query = user_query
        if "gcs_uri" in metadata and intent == "csv":
            augmented_query = (
                f"{user_query}\n[CSV file: {metadata['gcs_uri']}]"
            )
        elif "image_uri" in metadata and intent == "multimodal":
            augmented_query = (
                f"{user_query}\n[Image: {metadata['image_uri']}]"
            )

        # All intents run through RAGAgent – it selects the right tools
        result = self._rag_agent.run(
            user_query=augmented_query,
            session_id=session_id,
            conversation_history=conversation_history,
        )

        total_latency = int((time.time() - start) * 1000)
        result["intent"] = intent
        result["agent_used"] = "RAGAgent"
        result["orchestrator_latency_ms"] = total_latency

        return result

    # ──────────────────────────────────────────────
    # Batch processing
    # ──────────────────────────────────────────────

    def run_batch(
        self, queries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process a list of queries sequentially.

        Each item in `queries` should have:
            - query (str)
            - session_id (str, optional)
            - metadata (dict, optional)
        """
        results = []
        for item in queries:
            result = self.run(
                user_query=item.get("query", ""),
                session_id=item.get("session_id"),
                metadata=item.get("metadata", {}),
            )
            results.append(result)
        return results
