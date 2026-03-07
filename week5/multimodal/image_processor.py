"""
Week 5 - Image Processor using Gemini Vision (Gemini 2.0 Flash multimodal).

Capabilities:
  - OCR: extract text from images, scanned documents, screenshots
  - Visual Q&A: answer questions grounded in image content
  - Object/Entity detection: list key entities in an image
  - Chart/Table extraction: parse data from charts and tables
  - Image classification: categorise the type/subject of an image
  - Batch processing: process multiple images in parallel

Supported input formats:
  - GCS URI      : gs://bucket/image.png
  - HTTP/HTTPS   : https://domain/image.jpg
  - Base64 URI   : data:image/jpeg;base64,<data>
  - Raw bytes    : (mime_type required)
"""

import base64
import io
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig, Part

logger = logging.getLogger(__name__)


class ImageProcessor:
    """
    Processes images using Gemini's multimodal capability.
    """

    # ── System prompt ──────────────────────────────
    VISION_SYSTEM = (
        "You are an expert visual analyst powered by Gemini Vision. "
        "Analyse images with high accuracy. Always structure your response clearly."
    )

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
        self._model = GenerativeModel(
            model_name,
            system_instruction=self.VISION_SYSTEM,
        )
        self._gen_config = GenerationConfig(
            temperature=0.1,
            max_output_tokens=2048,
        )

        logger.info(f"ImageProcessor ready | model={model_name}")

    # ──────────────────────────────────────────────
    # Image loading helpers
    # ──────────────────────────────────────────────

    def _load_image_part(
        self,
        image_source: str,
        mime_type: str = "image/jpeg",
        raw_bytes: Optional[bytes] = None,
    ) -> Part:
        """Convert an image source to a Gemini Part."""
        if raw_bytes is not None:
            return Part.from_data(data=raw_bytes, mime_type=mime_type)

        if image_source.startswith("gs://"):
            # Infer mime type from extension
            ext = image_source.rsplit(".", 1)[-1].lower()
            mime_map = {
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "png": "image/png",
                "gif": "image/gif",
                "webp": "image/webp",
                "bmp": "image/bmp",
                "tiff": "image/tiff",
                "pdf": "application/pdf",
            }
            mt = mime_map.get(ext, mime_type)
            return Part.from_uri(image_source, mime_type=mt)

        if image_source.startswith("data:"):
            header, b64data = image_source.split(",", 1)
            mt = header.split(";")[0].replace("data:", "")
            raw = base64.b64decode(b64data)
            return Part.from_data(data=raw, mime_type=mt)

        # HTTP/HTTPS URL
        try:
            import httpx
            resp = httpx.get(image_source, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            mt = resp.headers.get("content-type", mime_type).split(";")[0]
            return Part.from_data(data=resp.content, mime_type=mt)
        except ImportError:
            raise RuntimeError(
                "httpx is required for HTTP image loading. "
                "Install with: pip install httpx"
            )

    # ──────────────────────────────────────────────
    # Core capabilities
    # ──────────────────────────────────────────────

    def extract_text(
        self,
        image_source: str,
        language_hint: str = "auto",
        raw_bytes: Optional[bytes] = None,
        mime_type: str = "image/jpeg",
    ) -> Dict[str, Any]:
        """
        Perform OCR on an image and extract all visible text.

        Returns:
            dict with 'extracted_text', 'language', 'confidence', 'latency_ms'
        """
        start = time.time()
        try:
            image_part = self._load_image_part(image_source, mime_type, raw_bytes)
            lang_instruction = (
                f" The image may contain text in {language_hint}."
                if language_hint != "auto"
                else ""
            )
            prompt = (
                f"Extract ALL visible text from this image exactly as it appears.{lang_instruction}\n"
                "Format the extracted text preserving the original layout as much as possible.\n"
                "Then on the last line write: Language: <detected_language>"
            )

            resp = self._model.generate_content(
                [image_part, Part.from_text(prompt)],
                generation_config=self._gen_config,
            )
            full_text = resp.text or ""

            # Parse language from last line
            lines = full_text.strip().splitlines()
            language = "unknown"
            extracted = full_text
            if lines and lines[-1].startswith("Language:"):
                language = lines[-1].replace("Language:", "").strip()
                extracted = "\n".join(lines[:-1]).strip()

            return {
                "extracted_text": extracted,
                "language": language,
                "image_source": image_source,
                "latency_ms": int((time.time() - start) * 1000),
            }

        except Exception as exc:
            logger.error(f"extract_text failed: {exc}")
            return {"error": str(exc), "extracted_text": "", "image_source": image_source}

    def answer_question(
        self,
        image_source: str,
        question: str,
        context: Optional[str] = None,
        raw_bytes: Optional[bytes] = None,
        mime_type: str = "image/jpeg",
    ) -> Dict[str, Any]:
        """
        Answer a specific question about the image (Visual Q&A).
        Optionally enriched with text context (RAG-augmented vision).
        """
        start = time.time()
        try:
            image_part = self._load_image_part(image_source, mime_type, raw_bytes)

            context_block = f"\nAdditional context:\n{context}\n" if context else ""
            prompt = (
                f"Look at this image carefully and answer the following question.\n"
                f"{context_block}\n"
                f"Question: {question}\n\n"
                "Be specific, concise, and base your answer on what is visible in the image."
            )

            resp = self._model.generate_content(
                [image_part, Part.from_text(prompt)],
                generation_config=self._gen_config,
            )

            return {
                "question": question,
                "answer": resp.text.strip() if resp else "",
                "image_source": image_source,
                "latency_ms": int((time.time() - start) * 1000),
            }

        except Exception as exc:
            logger.error(f"answer_question failed: {exc}")
            return {"error": str(exc), "question": question, "answer": ""}

    def describe_image(
        self,
        image_source: str,
        detail_level: str = "standard",
        raw_bytes: Optional[bytes] = None,
        mime_type: str = "image/jpeg",
    ) -> Dict[str, Any]:
        """
        Generate a structured description of the image.

        detail_level: 'brief' | 'standard' | 'detailed'
        """
        start = time.time()
        detail_instructions = {
            "brief": "Provide a single-sentence description of the image.",
            "standard": (
                "Describe the image in 3-5 sentences covering: "
                "main subject, setting, key objects, colors, and any text visible."
            ),
            "detailed": (
                "Provide a comprehensive description including: "
                "1) Main subject and action, "
                "2) Background/setting, "
                "3) All visible objects and their positions, "
                "4) Colors and visual style, "
                "5) Any text or numbers visible, "
                "6) Overall mood or context."
            ),
        }
        instruction = detail_instructions.get(detail_level, detail_instructions["standard"])

        try:
            image_part = self._load_image_part(image_source, mime_type, raw_bytes)
            resp = self._model.generate_content(
                [image_part, Part.from_text(instruction)],
                generation_config=self._gen_config,
            )

            return {
                "description": resp.text.strip() if resp else "",
                "detail_level": detail_level,
                "image_source": image_source,
                "latency_ms": int((time.time() - start) * 1000),
            }

        except Exception as exc:
            logger.error(f"describe_image failed: {exc}")
            return {"error": str(exc), "description": "", "image_source": image_source}

    def extract_table_data(
        self,
        image_source: str,
        output_format: str = "json",
        raw_bytes: Optional[bytes] = None,
        mime_type: str = "image/jpeg",
    ) -> Dict[str, Any]:
        """
        Extract tabular data from an image of a table or spreadsheet.

        output_format: 'json' | 'csv' | 'markdown'
        """
        start = time.time()
        format_instructions = {
            "json": "Return the table data as a JSON array of objects where keys are column headers.",
            "csv": "Return the table data in CSV format with the first row as headers.",
            "markdown": "Return the table data as a Markdown table.",
        }
        fmt_instruction = format_instructions.get(output_format, format_instructions["json"])

        try:
            image_part = self._load_image_part(image_source, mime_type, raw_bytes)
            prompt = (
                "This image contains a table or spreadsheet. "
                "Extract ALL the data from the table. "
                f"{fmt_instruction}\n"
                "If there are multiple tables, extract all of them and label each."
            )

            resp = self._model.generate_content(
                [image_part, Part.from_text(prompt)],
                generation_config=GenerationConfig(temperature=0.0, max_output_tokens=4096),
            )
            raw_output = resp.text.strip() if resp else ""

            result: Dict[str, Any] = {
                "raw_output": raw_output,
                "output_format": output_format,
                "image_source": image_source,
                "latency_ms": int((time.time() - start) * 1000),
            }

            # Try to parse JSON for structured output
            if output_format == "json":
                try:
                    import json as _json
                    start_idx = raw_output.find("[")
                    end_idx = raw_output.rfind("]") + 1
                    if start_idx >= 0 and end_idx > start_idx:
                        result["structured_data"] = _json.loads(
                            raw_output[start_idx:end_idx]
                        )
                except Exception:
                    pass

            return result

        except Exception as exc:
            logger.error(f"extract_table_data failed: {exc}")
            return {"error": str(exc), "image_source": image_source}

    def classify_image(
        self,
        image_source: str,
        categories: Optional[List[str]] = None,
        raw_bytes: Optional[bytes] = None,
        mime_type: str = "image/jpeg",
    ) -> Dict[str, Any]:
        """
        Classify the image into predefined or open categories.

        If `categories` is provided, classify into one of those.
        Otherwise, auto-detect the most suitable category.
        """
        start = time.time()
        try:
            image_part = self._load_image_part(image_source, mime_type, raw_bytes)

            if categories:
                cats_str = ", ".join(categories)
                prompt = (
                    f"Classify this image into EXACTLY ONE of these categories: {cats_str}\n"
                    "Return only the category name, nothing else."
                )
            else:
                prompt = (
                    "What type/category best describes this image? "
                    "Be specific (e.g., 'invoice', 'chart', 'photograph', 'diagram', etc.). "
                    "Return only the category name."
                )

            resp = self._model.generate_content(
                [image_part, Part.from_text(prompt)],
                generation_config=GenerationConfig(temperature=0.0, max_output_tokens=50),
            )
            category = resp.text.strip() if resp else "unknown"

            return {
                "category": category,
                "available_categories": categories,
                "image_source": image_source,
                "latency_ms": int((time.time() - start) * 1000),
            }

        except Exception as exc:
            logger.error(f"classify_image failed: {exc}")
            return {"error": str(exc), "category": "unknown", "image_source": image_source}

    # ──────────────────────────────────────────────
    # Batch processing
    # ──────────────────────────────────────────────

    def batch_analyze(
        self,
        image_sources: List[str],
        task: str = "describe",
        question: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Process multiple images with the same task.

        task: 'describe' | 'ocr' | 'classify' | 'qa'
        """
        results = []
        for src in image_sources:
            try:
                if task == "describe":
                    result = self.describe_image(src)
                elif task == "ocr":
                    result = self.extract_text(src)
                elif task == "classify":
                    result = self.classify_image(src)
                elif task == "qa" and question:
                    result = self.answer_question(src, question)
                else:
                    result = self.describe_image(src)
            except Exception as exc:
                result = {"error": str(exc), "image_source": src}

            results.append(result)

        return results
