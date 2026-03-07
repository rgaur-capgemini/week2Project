"""
Week 5 - Multimodal Pipeline

Combines image processing (Gemini Vision) with RAG document retrieval
to answer questions that require understanding BOTH visual and textual data.

Use-cases:
  - "What does this invoice say? Compare it with our pricing policy."
  - "Analyse this chart and explain the trend relative to our KPI docs."
  - "OCR this scanned form and store the structured data."
  - "Identify objects in these images and find related documents."

Pipeline Flow:
    Image(s) + Query
        ↓
    Image Analysis   (ImageProcessor)
        ↓
    OCR / Description
        ↓
    RAG Retrieval    (EnhancedRAGPipeline – text context augmentation)
        ↓
    Combined Prompt  (image analysis + retrieved docs)
        ↓
    Gemini Generation
        ↓
    Structured Response
"""

import logging
import time
from typing import Any, Dict, List, Optional

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig, Part

from week5.multimodal.image_processor import ImageProcessor
from week5.rag.enhanced_rag_pipeline import EnhancedRAGPipeline

logger = logging.getLogger(__name__)


class MultimodalPipeline:
    """
    End-to-end multimodal pipeline: images + text + RAG → answer.
    """

    MULTIMODAL_PROMPT = """You are an advanced AI assistant with vision and document analysis capabilities.

Image Analysis Results:
{image_analysis}

Retrieved Document Context:
{doc_context}

User Question: {question}

Instructions:
- Combine insights from BOTH the image analysis and the document context.
- Be specific about which information came from the image vs. documents.
- If there are contradictions, flag them.
- Provide a comprehensive, structured answer.
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

        self.image_processor = ImageProcessor(
            project_id=project_id,
            location=location,
            model_name=model_name,
        )
        self.rag_pipeline = EnhancedRAGPipeline(
            project_id=project_id,
            location=location,
            model_name=model_name,
            enable_decomposition=False,  # keep fast for multimodal
            enable_self_eval=False,
        )
        self._model = GenerativeModel(model_name)
        self._gen_config = GenerationConfig(temperature=0.2, max_output_tokens=4096)

        logger.info(f"MultimodalPipeline ready | model={model_name}")

    # ──────────────────────────────────────────────
    # Core pipeline
    # ──────────────────────────────────────────────

    def process(
        self,
        question: str,
        image_sources: Optional[List[str]] = None,
        raw_images: Optional[List[Dict]] = None,  # [{"bytes": b"...", "mime_type": "image/jpeg"}]
        enable_rag: bool = True,
        image_task: str = "describe",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a multimodal query combining images and RAG retrieval.

        Args:
            question: The user's question.
            image_sources: List of GCS URIs / HTTP URLs / base64 URIs.
            raw_images: List of dicts with 'bytes' and 'mime_type'.
            enable_rag: Whether to augment with document retrieval.
            image_task: 'describe' | 'ocr' | 'qa' | 'table' | 'classify'
            session_id: Optional session tracking ID.

        Returns:
            answer, image_analyses, rag_context, sources, latency_ms
        """
        start = time.time()
        all_sources = list(image_sources or [])

        # ── Validate input ─────────────────────────
        if not all_sources and not raw_images:
            # Text-only fallback to RAG
            if enable_rag:
                rag_result = self.rag_pipeline.query(question, session_id=session_id)
                return {
                    "answer": rag_result["answer"],
                    "image_analyses": [],
                    "rag_context": rag_result.get("answer", ""),
                    "sources": rag_result.get("sources", []),
                    "mode": "rag_only",
                    "latency_ms": int((time.time() - start) * 1000),
                    "session_id": session_id,
                }
            return {"error": "No images provided.", "answer": ""}

        # ── Step 1: Analyse images ─────────────────
        image_analyses: List[Dict] = []

        for src in all_sources:
            try:
                if image_task == "ocr":
                    analysis = self.image_processor.extract_text(src)
                elif image_task == "table":
                    analysis = self.image_processor.extract_table_data(src, output_format="json")
                elif image_task == "classify":
                    analysis = self.image_processor.classify_image(src)
                elif image_task == "qa":
                    analysis = self.image_processor.answer_question(src, question)
                else:
                    # 'describe' – always useful as base analysis
                    analysis = self.image_processor.describe_image(src, detail_level="standard")

                image_analyses.append({"source": src, "task": image_task, **analysis})
            except Exception as exc:
                logger.error(f"Image analysis failed for {src}: {exc}")
                image_analyses.append({"source": src, "error": str(exc)})

        # Process raw image bytes
        for raw_img in (raw_images or []):
            try:
                raw_bytes = raw_img.get("bytes", b"")
                mime_type = raw_img.get("mime_type", "image/jpeg")
                label = raw_img.get("label", "uploaded_image")

                if image_task == "ocr":
                    analysis = self.image_processor.extract_text(
                        "", raw_bytes=raw_bytes, mime_type=mime_type
                    )
                elif image_task == "qa":
                    analysis = self.image_processor.answer_question(
                        "", question, raw_bytes=raw_bytes, mime_type=mime_type
                    )
                else:
                    analysis = self.image_processor.describe_image(
                        "", raw_bytes=raw_bytes, mime_type=mime_type
                    )

                image_analyses.append({"source": label, "task": image_task, **analysis})
            except Exception as exc:
                logger.error(f"Raw image analysis failed: {exc}")

        # ── Step 2: Build image analysis summary ───
        image_summary_parts = []
        for a in image_analyses:
            src = a.get("source", "image")
            if "error" in a:
                image_summary_parts.append(f"[{src}]: Error - {a['error']}")
            elif image_task == "ocr":
                image_summary_parts.append(f"[{src}] OCR Text:\n{a.get('extracted_text', '')}")
            elif image_task == "table":
                image_summary_parts.append(
                    f"[{src}] Table Data:\n{a.get('raw_output', '')}"
                )
            elif image_task == "qa":
                image_summary_parts.append(f"[{src}] Answer:\n{a.get('answer', '')}")
            elif image_task == "classify":
                image_summary_parts.append(f"[{src}] Category: {a.get('category', '')}")
            else:
                image_summary_parts.append(f"[{src}] Description:\n{a.get('description', '')}")

        image_analysis_text = "\n\n".join(image_summary_parts)

        # ── Step 3: RAG retrieval ──────────────────
        rag_context = ""
        rag_sources: List[str] = []
        if enable_rag:
            # Augment the query with image content for better retrieval
            augmented_query = f"{question}\n\nImage content hint: {image_analysis_text[:500]}"
            try:
                rag_result = self.rag_pipeline.query(augmented_query, session_id=session_id)
                rag_context = rag_result.get("answer", "")
                rag_sources = rag_result.get("sources", [])
            except Exception as rag_err:
                logger.warning(f"RAG retrieval failed: {rag_err}")

        # ── Step 4: Combine + generate ─────────────
        if rag_context:
            prompt = self.MULTIMODAL_PROMPT.format(
                image_analysis=image_analysis_text[:3000],
                doc_context=rag_context[:2000],
                question=question,
            )
            resp = self._model.generate_content(prompt, generation_config=self._gen_config)
            final_answer = resp.text.strip() if resp else image_analysis_text
            mode = "multimodal_rag"
        else:
            # Image-only answer
            final_answer = image_analysis_text
            mode = "image_only"

        latency_ms = int((time.time() - start) * 1000)
        logger.info(
            f"MultimodalPipeline complete | images={len(image_analyses)} | "
            f"rag={enable_rag} | mode={mode} | latency_ms={latency_ms}"
        )

        return {
            "answer": final_answer,
            "image_analyses": image_analyses,
            "rag_context": rag_context,
            "sources": rag_sources,
            "mode": mode,
            "latency_ms": latency_ms,
            "session_id": session_id,
        }

    # ──────────────────────────────────────────────
    # Convenience methods
    # ──────────────────────────────────────────────

    def analyze_invoice(self, image_source: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Extract and analyse invoice data using OCR + RAG."""
        return self.process(
            question="Extract all invoice details: vendor, date, line items, totals, and payment terms.",
            image_sources=[image_source],
            image_task="ocr",
            enable_rag=True,
            session_id=session_id,
        )

    def analyze_chart(
        self,
        image_source: str,
        question: str = "What trends and insights does this chart show?",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyse a chart image and correlate with RAG documents."""
        return self.process(
            question=question,
            image_sources=[image_source],
            image_task="describe",
            enable_rag=True,
            session_id=session_id,
        )

    def batch_ocr(
        self,
        image_sources: List[str],
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """OCR multiple images without RAG augmentation."""
        results = []
        for src in image_sources:
            result = self.process(
                question="Extract all text.",
                image_sources=[src],
                image_task="ocr",
                enable_rag=False,
                session_id=session_id,
            )
            results.append(result)
        return results
