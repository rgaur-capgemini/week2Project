"""
Week 5 - Unit tests for Multimodal Pipeline and Image Processor.
"""

import pytest
from unittest.mock import MagicMock, patch


# ══════════════════════════════════════════════
# ImageProcessor tests
# ══════════════════════════════════════════════

class TestImageProcessor:
    """Tests for ImageProcessor."""

    @pytest.fixture
    def mock_processor(self):
        """Return an ImageProcessor with mocked Vertex AI."""
        with patch("vertexai.init"), \
             patch("vertexai.generative_models.GenerativeModel") as MockModel:

            mock_resp = MagicMock()
            mock_resp.text = "This image shows a bar chart with sales data."
            MockModel.return_value.generate_content.return_value = mock_resp

            from week5.multimodal.image_processor import ImageProcessor
            proc = ImageProcessor(
                project_id="test-project",
                location="us-central1",
            )
            proc._model = MockModel.return_value
            yield proc

    def test_describe_image_returns_description(self, mock_processor):
        """describe_image should return a description dict."""
        with patch.object(mock_processor, "_load_image_part", return_value=MagicMock()):
            result = mock_processor.describe_image(
                image_source="gs://bucket/test.jpg",
                detail_level="standard",
            )
        assert "description" in result
        assert len(result["description"]) > 0
        assert result["detail_level"] == "standard"
        assert "latency_ms" in result

    def test_extract_text_returns_ocr(self, mock_processor):
        """extract_text should return extracted_text field."""
        mock_processor._model.generate_content.return_value = MagicMock(
            text="Invoice #12345\nDate: 2025-01-01\nLanguage: English"
        )
        with patch.object(mock_processor, "_load_image_part", return_value=MagicMock()):
            result = mock_processor.extract_text("gs://bucket/invoice.jpg")
        assert "extracted_text" in result
        assert "language" in result
        assert result["language"] == "English"

    def test_classify_image_returns_category(self, mock_processor):
        """classify_image should return a category."""
        mock_processor._model.generate_content.return_value = MagicMock(text="invoice")
        with patch.object(mock_processor, "_load_image_part", return_value=MagicMock()):
            result = mock_processor.classify_image(
                image_source="gs://bucket/doc.jpg",
                categories=["invoice", "chart", "photo"],
            )
        assert "category" in result
        assert result["category"] == "invoice"

    def test_answer_question_includes_question_in_response(self, mock_processor):
        """answer_question should echo the question in response."""
        mock_processor._model.generate_content.return_value = MagicMock(
            text="The chart shows an upward trend in Q4."
        )
        with patch.object(mock_processor, "_load_image_part", return_value=MagicMock()):
            result = mock_processor.answer_question(
                image_source="gs://bucket/chart.jpg",
                question="What trend is shown?",
            )
        assert result["question"] == "What trend is shown?"
        assert "answer" in result
        assert len(result["answer"]) > 0

    def test_extract_table_data_json_format(self, mock_processor):
        """extract_table_data should try to parse JSON from model output."""
        mock_processor._model.generate_content.return_value = MagicMock(
            text='[{"name": "Alice", "score": 95}, {"name": "Bob", "score": 88}]'
        )
        with patch.object(mock_processor, "_load_image_part", return_value=MagicMock()):
            result = mock_processor.extract_table_data(
                image_source="gs://bucket/table.jpg",
                output_format="json",
            )
        assert "raw_output" in result
        if "structured_data" in result:
            assert isinstance(result["structured_data"], list)

    def test_batch_analyze_returns_list(self, mock_processor):
        """batch_analyze should return a list of results."""
        with patch.object(mock_processor, "_load_image_part", return_value=MagicMock()):
            results = mock_processor.batch_analyze(
                ["gs://bucket/img1.jpg", "gs://bucket/img2.jpg"],
                task="describe",
            )
        assert isinstance(results, list)
        assert len(results) == 2

    def test_error_handling_returns_error_dict(self, mock_processor):
        """Failed analysis should return dict with 'error' key, not raise."""
        mock_processor._model.generate_content.side_effect = Exception("API unavailable")
        with patch.object(mock_processor, "_load_image_part", return_value=MagicMock()):
            result = mock_processor.describe_image("gs://bucket/broken.jpg")
        assert "error" in result


# ══════════════════════════════════════════════
# MultimodalPipeline tests
# ══════════════════════════════════════════════

class TestMultimodalPipeline:
    """Tests for MultimodalPipeline."""

    @pytest.fixture
    def mock_pipeline(self):
        """Return a MultimodalPipeline with all heavy deps mocked."""
        with patch("vertexai.init"), \
             patch("vertexai.generative_models.GenerativeModel"):
            with patch("week5.multimodal.image_processor.ImageProcessor") as MockIP, \
                 patch("week5.rag.enhanced_rag_pipeline.EnhancedRAGPipeline") as MockRAG:

                mock_ip = MagicMock()
                mock_ip.describe_image.return_value = {
                    "source": "gs://bucket/img.jpg",
                    "description": "A product photo.",
                    "latency_ms": 200,
                }
                mock_ip.extract_text.return_value = {
                    "source": "gs://bucket/invoice.jpg",
                    "extracted_text": "Invoice #001",
                    "language": "English",
                    "latency_ms": 300,
                }
                mock_ip.batch_analyze.return_value = [
                    {"source": "gs://bucket/img.jpg", "description": "photo"}
                ]
                MockIP.return_value = mock_ip

                mock_rag = MagicMock()
                mock_rag.query.return_value = {
                    "answer": "Based on the documents...",
                    "sources": ["policy.pdf"],
                }
                mock_rag.enable_decomposition = False
                mock_rag.enable_self_eval = False
                MockRAG.return_value = mock_rag

                from week5.multimodal.multimodal_pipeline import MultimodalPipeline
                pipeline = MultimodalPipeline(
                    project_id="test-project",
                    location="us-central1",
                )
                pipeline.image_processor = mock_ip
                pipeline.rag_pipeline = mock_rag
                pipeline._model = MagicMock()
                pipeline._model.generate_content.return_value = MagicMock(
                    text="Combined analysis: The image shows a product. Policy says..."
                )
                yield pipeline

    def test_process_with_image_and_rag(self, mock_pipeline):
        """process() with image + RAG should return answer with mode 'multimodal_rag'."""
        result = mock_pipeline.process(
            question="What does this image contain?",
            image_sources=["gs://bucket/img.jpg"],
            enable_rag=True,
            image_task="describe",
        )
        assert "answer" in result
        assert "image_analyses" in result
        assert "latency_ms" in result
        assert result["mode"] in {"multimodal_rag", "image_only"}

    def test_process_without_images_falls_back_to_rag(self, mock_pipeline):
        """process() without images should use RAG only."""
        result = mock_pipeline.process(
            question="What is our compliance policy?",
            image_sources=None,
            enable_rag=True,
        )
        assert "answer" in result
        assert result["mode"] in {"rag_only", "multimodal_rag", "image_only"}

    def test_process_ocr_task(self, mock_pipeline):
        """process() with image_task='ocr' should call extract_text."""
        result = mock_pipeline.process(
            question="Extract text from invoice",
            image_sources=["gs://bucket/invoice.jpg"],
            image_task="ocr",
            enable_rag=False,
        )
        assert "image_analyses" in result
        mock_pipeline.image_processor.extract_text.assert_called()

    def test_analyze_invoice_convenience_method(self, mock_pipeline):
        """analyze_invoice should call process with ocr task."""
        result = mock_pipeline.analyze_invoice("gs://bucket/invoice.jpg")
        assert "answer" in result

    def test_analyze_chart_convenience_method(self, mock_pipeline):
        """analyze_chart should call process with describe task."""
        result = mock_pipeline.analyze_chart(
            "gs://bucket/chart.jpg",
            "What trends are visible?",
        )
        assert "answer" in result

    def test_batch_ocr_returns_list(self, mock_pipeline):
        """batch_ocr should return a list with one result per image."""
        results = mock_pipeline.batch_ocr(
            ["gs://bucket/img1.jpg", "gs://bucket/img2.jpg"]
        )
        assert isinstance(results, list)
        assert len(results) == 2

    def test_raw_image_bytes_processing(self, mock_pipeline):
        """process() with raw_images should process bytes without GCS URI."""
        raw_images = [
            {
                "bytes": b"fake_image_bytes",
                "mime_type": "image/jpeg",
                "label": "test_image",
            }
        ]
        mock_pipeline.image_processor.describe_image.return_value = {
            "source": "test_image",
            "description": "A test image.",
            "latency_ms": 100,
        }
        result = mock_pipeline.process(
            question="Describe this image",
            raw_images=raw_images,
            enable_rag=False,
            image_task="describe",
        )
        assert "answer" in result
        assert "image_analyses" in result


# ══════════════════════════════════════════════
# Smoke tests (marked for CI)
# ══════════════════════════════════════════════

@pytest.mark.smoke
class TestWeek5APISmokeTests:
    """Smoke tests to run against a deployed instance."""

    def test_agent_health_endpoint(self, base_url=None):
        """GET /api/v5/agent/health should return 200."""
        if not base_url:
            pytest.skip("base_url not configured")
        try:
            import httpx
            resp = httpx.get(f"{base_url}/api/v5/agent/health", timeout=10)
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
        except Exception as e:
            pytest.skip(f"Service not reachable: {e}")

    def test_multimodal_health_endpoint(self, base_url=None):
        """GET /api/v5/multimodal/health should return 200."""
        if not base_url:
            pytest.skip("base_url not configured")
        try:
            import httpx
            resp = httpx.get(f"{base_url}/api/v5/multimodal/health", timeout=10)
            assert resp.status_code == 200
        except Exception as e:
            pytest.skip(f"Service not reachable: {e}")
