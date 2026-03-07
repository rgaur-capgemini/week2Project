"""
Week 5 - Enhanced RAG Pipeline

Extends the existing LangGraph RAG pipeline with:
  1. CSV-aware retrieval (structured + unstructured chunks)
  2. Query decomposition for multi-hop questions
  3. Self-evaluation and answer confidence scoring
  4. Source diversity filtering (avoid same-document dominance)
  5. Contextual compression to fit more relevant context in prompt

Flow:
    User Query
        ↓
    Query Decomposition  (break complex Q into sub-queries)
        ↓
    Parallel Retrieval   (vector search for each sub-query)
        ↓
    Source Diversity Filter
        ↓
    Contextual Compression (semantic filter + token limit)
        ↓
    Gemini Generation
        ↓
    Self-Evaluation (confidence, hallucination check)
        ↓
    Final Answer + Metadata
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

logger = logging.getLogger(__name__)


class EnhancedRAGPipeline:
    """
    Production-grade RAG pipeline with CSV support, query decomposition,
    and self-evaluation built on top of the existing Week 1–4 stack.
    """

    DECOMPOSITION_PROMPT = """Break the following complex question into 2-4 simpler sub-questions.
Return ONLY a JSON array of strings. No explanations.

Question: {question}

Example output: ["sub-question 1", "sub-question 2", "sub-question 3"]"""

    GENERATION_PROMPT = """You are a helpful AI assistant. Answer the question based ONLY on the provided context.
If the context doesn't contain enough information, say so clearly.

Context:
{context}

Question: {question}

Instructions:
- Be concise and accurate.
- Cite relevant sources at the end.
- If data comes from a CSV, mention the column names used.
- Confidence level: rate 0-100 after your answer on the line starting with "Confidence:"
"""

    EVALUATION_PROMPT = """Evaluate this RAG answer for quality:

Question: {question}
Answer: {answer}
Context used: {context_preview}

Rate on a scale of 0-100 for each criterion (JSON format only):
- faithfulness: Is the answer grounded in the context?
- relevance: Does the answer address the question?
- completeness: Are all aspects of the question addressed?
- hallucination_risk: Likelihood the answer contains fabricated info (0=none, 100=high)

Return: {{"faithfulness": <int>, "relevance": <int>, "completeness": <int>, "hallucination_risk": <int>}}"""

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model_name: str = "gemini-2.0-flash-001",
        top_k: int = 8,
        max_context_tokens: int = 6000,
        enable_decomposition: bool = True,
        enable_self_eval: bool = True,
    ):
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self.top_k = top_k
        self.max_context_tokens = max_context_tokens
        self.enable_decomposition = enable_decomposition
        self.enable_self_eval = enable_self_eval

        vertexai.init(project=project_id, location=location)

        self._model = GenerativeModel(model_name)
        self._gen_config = GenerationConfig(temperature=0.2, max_output_tokens=4096)

        # Lazy-init heavy clients
        self._embedder = None
        self._vector_store = None
        self._reranker = None

    # ──────────────────────────────────────────────
    # Client initialisation
    # ──────────────────────────────────────────────

    def _ensure_clients(self):
        if self._embedder is not None:
            return

        from app.config import config as app_config
        from app.rag.vector_store import VertexVectorStore
        from app.rag.reranker import HybridReranker

        # embedder kept for potential future use; search() embeds internally
        from app.rag.embeddings import VertexTextEmbedder
        self._embedder = VertexTextEmbedder(
            project=app_config.PROJECT_ID,
            location=app_config.VERTEX_LOCATION,
        )
        self._vector_store = VertexVectorStore(
            project=app_config.PROJECT_ID,
            location=app_config.VERTEX_LOCATION,
            index_id=app_config.VERTEX_INDEX_ID,
            index_endpoint_name=app_config.VERTEX_INDEX_ENDPOINT,
            deployed_index_id=app_config.DEPLOYED_INDEX_ID,
        )
        self._reranker = HybridReranker(
            project=app_config.PROJECT_ID,
            location=app_config.VERTEX_LOCATION,
        )

    # ──────────────────────────────────────────────
    # Query decomposition
    # ──────────────────────────────────────────────

    def _decompose_query(self, question: str) -> List[str]:
        """Break a complex question into simpler sub-questions."""
        try:
            import json as _json

            prompt = self.DECOMPOSITION_PROMPT.format(question=question)
            resp = self._model.generate_content(
                prompt,
                generation_config=GenerationConfig(temperature=0.0, max_output_tokens=256),
            )
            text = resp.text.strip()
            # Extract JSON array
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                sub_qs = _json.loads(text[start:end])
                if isinstance(sub_qs, list) and sub_qs:
                    return [str(q) for q in sub_qs[:4]]
        except Exception as exc:
            logger.warning(f"Query decomposition failed: {exc}")

        return [question]  # fallback to original

    # ──────────────────────────────────────────────
    # Retrieval
    # ──────────────────────────────────────────────

    def _retrieve(self, query: str) -> List[Dict]:
        """Search Vector Search – embedding is handled internally by the store."""
        results = self._vector_store.search(query, top_k=self.top_k)
        return results or []

    def _deduplicate_results(self, all_results: List[Dict]) -> List[Dict]:
        """Remove duplicate chunks (same chunk_id) across sub-query results."""
        seen_ids = set()
        unique = []
        for r in all_results:
            cid = r.get("id", "")
            if cid not in seen_ids:
                seen_ids.add(cid)
                unique.append(r)
        return unique

    def _diversity_filter(self, results: List[Dict], max_per_source: int = 3) -> List[Dict]:
        """Limit chunks from the same source document to improve diversity."""
        source_counts: Dict[str, int] = {}
        filtered = []
        for r in results:
            src = r.get("metadata", {}).get("source", "unknown")
            cnt = source_counts.get(src, 0)
            if cnt < max_per_source:
                filtered.append(r)
                source_counts[src] = cnt + 1
        return filtered

    # ──────────────────────────────────────────────
    # Context building
    # ──────────────────────────────────────────────

    def _build_context(self, results: List[Dict]) -> Tuple[str, List[str]]:
        """
        Build context string from retrieved chunks within token budget.
        Returns (context_text, source_list).
        """
        context_parts = []
        sources = []
        token_budget = self.max_context_tokens
        approx_chars = token_budget * 4  # rough char estimate

        for i, r in enumerate(results):
            text = r.get("text", "")
            source = r.get("metadata", {}).get("source", f"chunk_{i}")
            chunk_type = r.get("metadata", {}).get("type", "document")

            prefix = f"[Source {i+1} | {chunk_type} | {source}]\n"
            entry = f"{prefix}{text}\n"

            if len("\n".join(context_parts)) + len(entry) > approx_chars:
                break

            context_parts.append(entry)
            if source not in sources:
                sources.append(source)

        return "\n---\n".join(context_parts), sources

    # ──────────────────────────────────────────────
    # Self-evaluation
    # ──────────────────────────────────────────────

    def _evaluate_answer(
        self,
        question: str,
        answer: str,
        context_preview: str,
    ) -> Dict[str, int]:
        """Score the generated answer using Gemini self-evaluation."""
        try:
            import json as _json

            prompt = self.EVALUATION_PROMPT.format(
                question=question,
                answer=answer,
                context_preview=context_preview[:500],
            )
            resp = self._model.generate_content(
                prompt,
                generation_config=GenerationConfig(temperature=0.0, max_output_tokens=128),
            )
            text = resp.text.strip()
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return _json.loads(text[start:end])
        except Exception as exc:
            logger.warning(f"Self-evaluation failed: {exc}")

        return {"faithfulness": -1, "relevance": -1, "completeness": -1, "hallucination_risk": -1}

    # ──────────────────────────────────────────────
    # Main pipeline
    # ──────────────────────────────────────────────

    def query(
        self,
        question: str,
        session_id: Optional[str] = None,
        filter_metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Run the enhanced RAG pipeline end-to-end.

        Returns:
            answer, sources, sub_queries, retrieval_results,
            evaluation, latency_ms, session_id
        """
        self._ensure_clients()
        start = time.time()

        # ── Step 1: Query decomposition ────────────
        sub_queries = [question]
        if self.enable_decomposition:
            sub_queries = self._decompose_query(question)
            logger.info(f"Decomposed into {len(sub_queries)} sub-queries")

        # ── Step 2: Parallel retrieval ─────────────
        all_results: List[Dict] = []
        for sq in sub_queries:
            results = self._retrieve(sq)
            all_results.extend(results)

        # ── Step 3: Dedup + diversity filter ───────
        all_results = self._deduplicate_results(all_results)
        all_results = self._diversity_filter(all_results)

        # ── Step 4: Rerank ─────────────────────────
        # HybridReranker.rerank(query, chunks: List[Dict]) → sorted List[Dict]
        # Each chunk dict gets a 'rerank_score' key added in-place.
        if self._reranker and all_results:
            try:
                all_results = self._reranker.rerank(question, all_results)
            except Exception as re_err:
                logger.warning(f"Reranking failed, using original order: {re_err}")

        # ── Step 5: Build context ──────────────────
        context, sources = self._build_context(all_results[: self.top_k])

        if not context.strip():
            return {
                "answer": "I could not find relevant information to answer your question.",
                "sources": [],
                "sub_queries": sub_queries,
                "retrieval_count": 0,
                "evaluation": {},
                "latency_ms": int((time.time() - start) * 1000),
                "session_id": session_id,
            }

        # ── Step 6: Generate answer ────────────────
        prompt = self.GENERATION_PROMPT.format(context=context, question=question)
        resp = self._model.generate_content(prompt, generation_config=self._gen_config)
        answer = resp.text.strip() if resp else "Generation failed."

        # ── Step 7: Self-evaluation ────────────────
        evaluation = {}
        if self.enable_self_eval:
            evaluation = self._evaluate_answer(question, answer, context[:500])

        latency_ms = int((time.time() - start) * 1000)
        logger.info(
            f"EnhancedRAG complete | session={session_id} | "
            f"sub_queries={len(sub_queries)} | chunks={len(all_results)} | "
            f"latency_ms={latency_ms}"
        )

        return {
            "answer": answer,
            "sources": sources,
            "sub_queries": sub_queries,
            "retrieval_count": len(all_results),
            "evaluation": evaluation,
            "latency_ms": latency_ms,
            "session_id": session_id,
            "model": self.model_name,
        }
