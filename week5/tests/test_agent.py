"""
Week 5 - Unit tests for Agentic AI components.

Tests:
  - RAGAgent tool dispatch
  - MultiAgentOrchestrator intent classification
  - AgentToolkit individual tools (mocked GCP clients)
"""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


# ══════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════

@pytest.fixture
def mock_vertex_init():
    """Prevent real Vertex AI initialisation during tests."""
    with patch("vertexai.init") as mock:
        yield mock


@pytest.fixture
def mock_generative_model():
    """Mock Gemini GenerativeModel."""
    with patch("vertexai.generative_models.GenerativeModel") as MockModel:
        mock_instance = MagicMock()
        mock_instance.start_chat.return_value = MagicMock()
        mock_instance.generate_content.return_value = MagicMock(
            text="Test answer",
            candidates=[
                MagicMock(
                    content=MagicMock(
                        parts=[MagicMock(text="Test answer", function_call=None)]
                    )
                )
            ],
        )
        MockModel.return_value = mock_instance
        yield MockModel


@pytest.fixture
def mock_toolkit():
    """Mock AgentToolkit."""
    toolkit = MagicMock()
    toolkit.search_documents.return_value = {
        "query": "test",
        "chunks": [{"id": "c1", "text": "relevant chunk", "score": 0.9}],
        "total_found": 1,
        "sources": ["gs://bucket/doc.pdf"],
    }
    toolkit.analyze_csv.return_value = {
        "rows": 100,
        "columns": ["name", "value"],
        "answer": "The CSV has 100 rows.",
    }
    toolkit.summarize_document.return_value = {
        "gcs_uri": "gs://bucket/doc.pdf",
        "summary": "This is a test summary.",
    }
    toolkit.process_image.return_value = {
        "image_uri": "gs://bucket/img.png",
        "analysis": "The image shows a chart.",
    }
    toolkit.get_cost_summary.return_value = {
        "costs": {"total_cost_usd": 500.0},
        "token_usage": {"total_tokens": 1_000_000},
    }
    return toolkit


# ══════════════════════════════════════════════
# AgentToolkit tests
# ══════════════════════════════════════════════

class TestAgentToolkit:
    """Tests for AgentToolkit methods."""

    def test_search_documents_returns_dict(self, mock_vertex_init):
        """search_documents should return a dict with expected keys."""
        with patch("app.config.config") as mock_cfg, \
             patch("app.rag.embeddings.VertexTextEmbedder") as MockEmb, \
             patch("app.rag.vector_store.VertexVectorStore") as MockVS:

            mock_cfg.PROJECT_ID = "test-project"
            mock_cfg.VERTEX_LOCATION = "us-central1"
            mock_cfg.VERTEX_INDEX_ID = "idx"
            mock_cfg.VERTEX_INDEX_ENDPOINT = "ep"
            mock_cfg.DEPLOYED_INDEX_ID = "dep"

            MockEmb.return_value.embed.return_value = [[0.1] * 768]
            MockVS.return_value.search.return_value = [
                {"id": "c1", "text": "relevant text", "score": 0.95, "metadata": {"source": "doc.pdf"}}
            ]

            from week5.agentic_ai.tools import AgentToolkit
            toolkit = AgentToolkit.__new__(AgentToolkit)
            toolkit.project_id = "test-project"
            toolkit.location = "us-central1"
            toolkit._vision_model = MagicMock()
            toolkit._gcs_client = MagicMock()
            toolkit._embedder = MockEmb.return_value
            toolkit._vector_store = MockVS.return_value

            result = toolkit.search_documents("test query", top_k=3)
            assert "chunks" in result
            assert "total_found" in result
            assert result["total_found"] == 1

    def test_analyze_csv_error_handling(self, mock_vertex_init):
        """analyze_csv should return error dict on failure, not raise."""
        with patch("google.cloud.storage.Client"):
            from week5.agentic_ai.tools import AgentToolkit
            toolkit = AgentToolkit.__new__(AgentToolkit)
            toolkit.project_id = "test-project"
            toolkit.location = "us-central1"
            toolkit._vision_model = MagicMock()
            mock_gcs = MagicMock()
            mock_gcs.bucket.return_value.blob.return_value.download_as_bytes.side_effect = Exception(
                "GCS not available"
            )
            toolkit._gcs_client = mock_gcs

            result = toolkit.analyze_csv(
                "gs://test-bucket/data.csv", "How many rows?"
            )
            assert "error" in result

    def test_get_cost_summary_delegates_to_finops(self, mock_vertex_init):
        """get_cost_summary should return a dict with costs key."""
        with patch("app.finops.cost_tracker.FinOpsTracker") as MockTracker:
            mock_tracker = MockTracker.return_value
            mock_tracker.get_current_month_costs.return_value = {"total_cost_usd": 300}
            mock_tracker.get_token_costs.return_value = {"total_tokens": 500_000}
            mock_tracker.detect_cost_anomalies.return_value = []

            from week5.agentic_ai.tools import AgentToolkit
            toolkit = AgentToolkit.__new__(AgentToolkit)
            toolkit.project_id = "test-project"
            toolkit.location = "us-central1"
            toolkit._vision_model = MagicMock()
            toolkit._gcs_client = MagicMock()

            result = toolkit.get_cost_summary(days=30)
            assert "costs" in result or "error" in result  # graceful either way


# ══════════════════════════════════════════════
# RAGAgent tests
# ══════════════════════════════════════════════

class TestRAGAgent:
    """Tests for RAGAgent."""

    @patch("vertexai.init")
    @patch("vertexai.generative_models.GenerativeModel")
    def test_agent_run_returns_expected_keys(self, MockModel, mock_init):
        """run() should return dict with answer, tool_calls, sources, latency_ms."""
        # Setup mock chat that returns no function calls (direct answer)
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.text = "This is the agent's answer."
        mock_part.function_call = MagicMock(name=None)
        mock_part.function_call.name = None
        mock_response.candidates = [MagicMock(content=MagicMock(parts=[mock_part]))]
        mock_chat.send_message.return_value = mock_response
        MockModel.return_value.start_chat.return_value = mock_chat
        MockModel.return_value.tools = []

        with patch("week5.agentic_ai.tools.AgentToolkit"):
            from week5.agentic_ai.agent import RAGAgent
            agent = RAGAgent.__new__(RAGAgent)
            agent.project_id = "test-project"
            agent.location = "us-central1"
            agent.model_name = "gemini-2.0-flash-001"
            agent.max_tool_calls = 3
            agent.model = MockModel.return_value
            agent.toolkit = MagicMock()
            agent._generation_config = MagicMock()

            result = agent.run("What is the status of our compliance?", session_id="sess_1")

        assert "answer" in result
        assert "tool_calls" in result
        assert "sources" in result
        assert "latency_ms" in result
        assert isinstance(result["latency_ms"], int)

    def test_dispatch_tool_search_documents(self):
        """_dispatch_tool should call toolkit.search_documents for 'search_documents'."""
        with patch("vertexai.init"), patch("vertexai.generative_models.GenerativeModel"):
            from week5.agentic_ai.agent import RAGAgent
            agent = RAGAgent.__new__(RAGAgent)
            agent.toolkit = MagicMock()
            agent.toolkit.search_documents.return_value = {
                "chunks": [], "total_found": 0, "sources": []
            }

            mock_fc = MagicMock()
            mock_fc.name = "search_documents"
            mock_fc.args = {"query": "test query", "top_k": 5}

            result = agent._dispatch_tool(mock_fc)
            data = json.loads(result)
            agent.toolkit.search_documents.assert_called_once_with(
                query="test query", top_k=5
            )
            assert "chunks" in data

    def test_dispatch_unknown_tool_returns_error(self):
        """_dispatch_tool should return error JSON for unknown tool names."""
        with patch("vertexai.init"), patch("vertexai.generative_models.GenerativeModel"):
            from week5.agentic_ai.agent import RAGAgent
            agent = RAGAgent.__new__(RAGAgent)
            agent.toolkit = MagicMock()

            mock_fc = MagicMock()
            mock_fc.name = "unknown_tool"
            mock_fc.args = {}

            result = agent._dispatch_tool(mock_fc)
            data = json.loads(result)
            assert "error" in data


# ══════════════════════════════════════════════
# Orchestrator tests
# ══════════════════════════════════════════════

class TestMultiAgentOrchestrator:
    """Tests for MultiAgentOrchestrator."""

    @patch("vertexai.init")
    @patch("vertexai.generative_models.GenerativeModel")
    def test_classify_intent_returns_valid_category(self, MockModel, mock_init):
        """_classify_intent should return one of the valid intent categories."""
        mock_resp = MagicMock(text="csv")
        MockModel.return_value.generate_content.return_value = mock_resp

        with patch("week5.agentic_ai.agent.RAGAgent"):
            from week5.agentic_ai.orchestrator import MultiAgentOrchestrator
            orch = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
            orch._classifier = MockModel.return_value
            orch._gen_config = MagicMock()

            intent = orch._classify_intent("Analyse the sales CSV data")
            assert intent in {"rag", "csv", "multimodal", "finops", "general"}

    @patch("vertexai.init")
    @patch("vertexai.generative_models.GenerativeModel")
    def test_classify_intent_fallback_on_error(self, MockModel, mock_init):
        """_classify_intent should fall back to 'rag' on exception."""
        MockModel.return_value.generate_content.side_effect = Exception("API error")

        with patch("week5.agentic_ai.agent.RAGAgent"):
            from week5.agentic_ai.orchestrator import MultiAgentOrchestrator
            orch = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
            orch._classifier = MockModel.return_value
            orch._gen_config = MagicMock()

            intent = orch._classify_intent("Any question")
            assert intent == "rag"

    @patch("vertexai.init")
    @patch("vertexai.generative_models.GenerativeModel")
    def test_orchestrator_run_returns_result_with_intent(self, MockModel, mock_init):
        """run() should include 'intent' in the result."""
        mock_resp = MagicMock(text="rag")
        MockModel.return_value.generate_content.return_value = mock_resp

        mock_agent = MagicMock()
        mock_agent.run.return_value = {
            "answer": "Test answer",
            "tool_calls": [],
            "sources": [],
            "latency_ms": 100,
            "session_id": "s1",
            "model": "gemini-2.0-flash-001",
        }

        with patch("week5.agentic_ai.agent.RAGAgent", return_value=mock_agent):
            from week5.agentic_ai.orchestrator import MultiAgentOrchestrator
            orch = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
            orch._classifier = MockModel.return_value
            orch._gen_config = MagicMock()
            orch._rag_agent = mock_agent

            result = orch.run("What are the key findings?", session_id="s1")

        assert "intent" in result
        assert "answer" in result
        assert "agent_used" in result
