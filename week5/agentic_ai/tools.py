"""
Week 5 - Agent Toolkit: Custom tool implementations for the RAGAgent.

Each method maps to a FunctionDeclaration and is dispatched by agent.py.
Tools cover: RAG search, CSV analysis, document summarisation, image analysis, cost info.
"""

import io
import json
import logging
import os
from typing import Any, Dict, List, Optional

import vertexai
from google.cloud import storage
from vertexai.generative_models import GenerativeModel, Part

logger = logging.getLogger(__name__)


class AgentToolkit:
    """
    Collection of callable tools used by the RAGAgent.

    Each public method must return a JSON-serialisable dict.
    """

    def __init__(self, project_id: str, location: str = "us-central1"):
        self.project_id = project_id
        self.location = location

        vertexai.init(project=project_id, location=location)

        # Vision model for multimodal tasks
        self._vision_model = GenerativeModel("gemini-2.0-flash-001")
        self._gcs_client = storage.Client(project=project_id)

        logger.info("AgentToolkit initialised")

    # ──────────────────────────────────────────────
    # Tool 1 – RAG document search
    # ──────────────────────────────────────────────

    def search_documents(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Search the Vertex AI Vector Search index for relevant document chunks.

        This method imports the existing RAG pipeline so Week 5 leverages
        the Week 1–4 embedder / vector store without duplication.
        """
        try:
            from app.config import config as app_config
            from app.rag.vector_store import VertexVectorStore

            vector_store = VertexVectorStore(
                project=app_config.PROJECT_ID,
                location=app_config.VERTEX_LOCATION,
                index_id=app_config.VERTEX_INDEX_ID,
                index_endpoint_name=app_config.VERTEX_INDEX_ENDPOINT,
                deployed_index_id=app_config.DEPLOYED_INDEX_ID,
            )

            # vector_store.search() handles embedding internally
            results = vector_store.search(query, top_k=top_k)

            chunks = []
            sources = []
            for r in results:
                chunks.append(
                    {
                        "id": r.get("id", ""),
                        "text": r.get("text", ""),
                        "score": r.get("score", 0.0),
                        "metadata": r.get("metadata", {}),
                    }
                )
                if r.get("metadata", {}).get("source"):
                    sources.append(r["metadata"]["source"])

            return {
                "query": query,
                "chunks": chunks,
                "total_found": len(chunks),
                "sources": sources,
            }

        except Exception as exc:
            logger.error(f"search_documents failed: {exc}")
            return {"query": query, "chunks": [], "total_found": 0, "error": str(exc)}

    # ──────────────────────────────────────────────
    # Tool 2 – CSV analysis
    # ──────────────────────────────────────────────

    def analyze_csv(
        self,
        gcs_uri: str,
        question: str,
        operation: str = "summary",
    ) -> Dict[str, Any]:
        """
        Load a CSV from GCS into pandas and answer questions about it.

        Operations: summary | filter | aggregate | sample
        """
        try:
            import pandas as pd

            # Parse bucket and blob from gs:// URI
            path = gcs_uri.replace("gs://", "")
            bucket_name, blob_name = path.split("/", 1)

            bucket = self._gcs_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            csv_bytes = blob.download_as_bytes()

            df = pd.read_csv(io.BytesIO(csv_bytes))

            base_info = {
                "rows": len(df),
                "columns": list(df.columns),
                "dtypes": df.dtypes.astype(str).to_dict(),
                "null_counts": df.isnull().sum().to_dict(),
                "gcs_uri": gcs_uri,
            }

            if operation == "summary":
                stats = df.describe(include="all").fillna("").to_dict()
                base_info["statistics"] = stats
                base_info["sample"] = df.head(5).to_dict(orient="records")

            elif operation == "sample":
                base_info["sample"] = df.head(10).to_dict(orient="records")

            elif operation == "aggregate":
                # Ask Gemini to write and conceptually execute the aggregation
                numeric_cols = df.select_dtypes(include="number").columns.tolist()
                base_info["numeric_summary"] = (
                    df[numeric_cols].describe().to_dict() if numeric_cols else {}
                )

            elif operation == "filter":
                # Return sample rows that are relevant to the question keyword
                keyword = question.split()[0] if question else ""
                mask = df.astype(str).apply(
                    lambda col: col.str.contains(keyword, case=False, na=False)
                ).any(axis=1)
                base_info["filtered_sample"] = df[mask].head(10).to_dict(orient="records")

            # Use Gemini to generate a natural-language answer about the data
            data_context = json.dumps(base_info, default=str)[:3000]
            prompt = (
                f"Given this CSV data context:\n{data_context}\n\n"
                f"Answer the following question:\n{question}"
            )
            answer_response = self._vision_model.generate_content(prompt)
            base_info["answer"] = answer_response.text if answer_response else ""

            return base_info

        except Exception as exc:
            logger.error(f"analyze_csv failed for {gcs_uri}: {exc}")
            return {"gcs_uri": gcs_uri, "error": str(exc)}

    # ──────────────────────────────────────────────
    # Tool 3 – Document summarisation
    # ──────────────────────────────────────────────

    def summarize_document(
        self,
        gcs_uri: str,
        focus: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Download a text/PDF document from GCS and summarise it with Gemini.
        """
        try:
            path = gcs_uri.replace("gs://", "")
            bucket_name, blob_name = path.split("/", 1)

            bucket = self._gcs_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            content_type = blob.content_type or ""
            raw_bytes = blob.download_as_bytes()

            # Decode text
            if "pdf" in content_type.lower():
                try:
                    from PyPDF2 import PdfReader

                    reader = PdfReader(io.BytesIO(raw_bytes))
                    text = "\n".join(
                        page.extract_text() or "" for page in reader.pages
                    )
                except Exception:
                    text = raw_bytes.decode("utf-8", errors="ignore")
            else:
                text = raw_bytes.decode("utf-8", errors="ignore")

            focus_instruction = f" Focus especially on: {focus}." if focus else ""
            prompt = (
                f"Summarise the following document concisely.{focus_instruction}\n\n"
                f"Document (first 4000 chars):\n{text[:4000]}"
            )

            response = self._vision_model.generate_content(prompt)
            summary = response.text if response else ""

            return {
                "gcs_uri": gcs_uri,
                "summary": summary,
                "char_count": len(text),
                "focus": focus,
            }

        except Exception as exc:
            logger.error(f"summarize_document failed for {gcs_uri}: {exc}")
            return {"gcs_uri": gcs_uri, "error": str(exc)}

    # ──────────────────────────────────────────────
    # Tool 4 – Image processing (Gemini Vision)
    # ──────────────────────────────────────────────

    def process_image(self, image_uri: str, question: str) -> Dict[str, Any]:
        """
        Analyse an image using Gemini Vision multimodal capability.

        Supports:
        - GCS URI:      gs://bucket/image.jpg
        - HTTPS URL:    https://...
        - Base64 URI:   data:image/jpeg;base64,...
        """
        try:
            if image_uri.startswith("gs://"):
                image_part = Part.from_uri(image_uri, mime_type="image/jpeg")
            elif image_uri.startswith("data:"):
                # base64 encoded
                header, b64data = image_uri.split(",", 1)
                mime = header.split(";")[0].replace("data:", "")
                import base64
                raw = base64.b64decode(b64data)
                image_part = Part.from_data(data=raw, mime_type=mime)
            else:
                # Treat as HTTP URL
                import httpx
                resp = httpx.get(image_uri, timeout=30)
                resp.raise_for_status()
                mime = resp.headers.get("content-type", "image/jpeg").split(";")[0]
                image_part = Part.from_data(data=resp.content, mime_type=mime)

            response = self._vision_model.generate_content(
                [
                    image_part,
                    Part.from_text(
                        f"Analyse this image and answer: {question}\n"
                        "Also provide: (1) a brief description, (2) any text visible (OCR), "
                        "(3) key objects or entities detected."
                    ),
                ]
            )

            return {
                "image_uri": image_uri,
                "question": question,
                "analysis": response.text if response else "",
            }

        except Exception as exc:
            logger.error(f"process_image failed for {image_uri}: {exc}")
            return {"image_uri": image_uri, "error": str(exc)}

    # ──────────────────────────────────────────────
    # Tool 5 – Cost summary (FinOps)
    # ──────────────────────────────────────────────

    def get_cost_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Return GCP cost and token usage summary by delegating to the
        existing FinOps cost_tracker module (Week 4).
        """
        try:
            from app.finops.cost_tracker import FinOpsTracker

            tracker = FinOpsTracker(project_id=self.project_id)
            costs = tracker.get_current_month_costs()
            tokens = tracker.get_token_costs(days=days)
            anomalies = tracker.detect_cost_anomalies()

            return {
                "period_days": days,
                "costs": costs,
                "token_usage": tokens,
                "anomalies": anomalies,
            }

        except Exception as exc:
            logger.error(f"get_cost_summary failed: {exc}")
            return {"error": str(exc)}
