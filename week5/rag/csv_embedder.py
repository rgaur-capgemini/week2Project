"""
Week 5 - CSV Embedder

Reads CSVs from GCS, converts each row (or group of rows) into a text
representation, embeds using Vertex AI text-embedding-004, and upserts
into the existing Vertex AI Vector Search index so the RAGAgent can
retrieve structured data alongside document chunks.

Flow:
    GCS CSV  →  Download  →  Row-to-text  →  Embed (batch)
             →  Upsert to Vector Search
             →  Store chunk metadata in Firestore
"""

import io
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from google.cloud import storage, firestore

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Text representation strategies
# ──────────────────────────────────────────────

def _row_to_text_key_value(row: pd.Series, columns: List[str]) -> str:
    """Convert a DataFrame row to 'col: value | col: value …' text."""
    parts = [f"{col}: {str(row[col]).strip()}" for col in columns if pd.notna(row[col])]
    return " | ".join(parts)


def _row_to_text_sentence(row: pd.Series, columns: List[str]) -> str:
    """Convert a DataFrame row to a natural-language sentence."""
    parts = []
    for col in columns:
        val = row[col]
        if pd.notna(val):
            parts.append(f"{col} is {val}")
    return ", ".join(parts) + "."


def _group_to_text(group: pd.DataFrame, group_col: str) -> str:
    """Summarise a group of rows sharing the same key column value."""
    group_val = group[group_col].iloc[0]
    cols = [c for c in group.columns if c != group_col]
    rows_text = "\n".join(
        _row_to_text_key_value(row, cols) for _, row in group.iterrows()
    )
    return f"{group_col}={group_val}:\n{rows_text}"


# ──────────────────────────────────────────────
# CSVEmbedder
# ──────────────────────────────────────────────

class CSVEmbedder:
    """
    Embeds CSV rows into Vertex AI Vector Search for RAG retrieval.

    Parameters
    ----------
    project_id : str
    location : str
    chunk_strategy : 'row' | 'group'
        - row   : one embedding per row (best for narrow tables)
        - group : one embedding per unique value of `group_column`
    group_column : str
        Column to group by when chunk_strategy='group'.
    batch_size : int
        Number of chunks per embedding API call.
    """

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        chunk_strategy: str = "row",
        group_column: Optional[str] = None,
        batch_size: int = 100,
    ):
        self.project_id = project_id
        self.location = location
        self.chunk_strategy = chunk_strategy
        self.group_column = group_column
        self.batch_size = batch_size

        self._gcs_client = storage.Client(project=project_id)

        # Lazy-load heavy GCP clients on first use
        self._embedder = None
        self._vector_store = None
        self._chunk_store = None

    def _init_clients(self):
        """Initialise Vertex AI clients (deferred to avoid import-time errors)."""
        if self._embedder is not None:
            return

        from app.config import config as app_config
        from app.rag.embeddings import VertexTextEmbedder
        from app.rag.vector_store import VertexVectorStore
        from app.storage.firestore_store import FirestoreChunkStore

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
        if app_config.USE_FIRESTORE:
            self._chunk_store = FirestoreChunkStore(
                project_id=app_config.PROJECT_ID,
                collection_name="csv_chunks",
            )

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    def embed_from_gcs(
        self,
        gcs_uri: str,
        source_label: Optional[str] = None,
        max_rows: int = 10_000,
    ) -> Dict[str, Any]:
        """
        Download a CSV from GCS, embed rows/groups, upsert to Vector Search.

        Returns a summary dict with ingestion stats.
        """
        self._init_clients()
        start = time.time()

        # ── Download CSV ───────────────────────────
        path = gcs_uri.replace("gs://", "")
        bucket_name, blob_name = path.split("/", 1)
        blob = self._gcs_client.bucket(bucket_name).blob(blob_name)
        csv_bytes = blob.download_as_bytes()
        df = pd.read_csv(io.BytesIO(csv_bytes)).head(max_rows)

        logger.info(f"CSV loaded: {gcs_uri} | rows={len(df)} cols={list(df.columns)}")

        # ── Convert rows to text chunks ────────────
        chunks = self._build_chunks(df, source_label or gcs_uri)

        if not chunks:
            return {"status": "empty", "gcs_uri": gcs_uri, "chunks_embedded": 0}

        # ── Batch embed ────────────────────────────
        all_ids = []
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i : i + self.batch_size]
            texts = [c["text"] for c in batch]
            vectors = self._embedder.embed(texts)

            # Upsert to Vertex AI Vector Search
            ids = self._vector_store.upsert(batch, vectors)
            all_ids.extend(ids)

            # Persist to Firestore
            if self._chunk_store:
                chunk_dict = {
                    ids[j]: {
                        "text": batch[j]["text"],
                        "metadata": batch[j].get("metadata", {}),
                        "vector": (
                            vectors[j].tolist()
                            if hasattr(vectors[j], "tolist")
                            else vectors[j]
                        ),
                    }
                    for j in range(len(batch))
                }
                self._chunk_store.batch_store_chunks(chunk_dict)

            logger.info(f"Embedded batch {i // self.batch_size + 1} | size={len(batch)}")

        duration_s = round(time.time() - start, 2)
        logger.info(
            f"CSV embedding complete | uri={gcs_uri} | "
            f"chunks={len(all_ids)} | duration={duration_s}s"
        )

        return {
            "status": "success",
            "gcs_uri": gcs_uri,
            "rows_processed": len(df),
            "chunks_embedded": len(all_ids),
            "chunk_ids": all_ids[:20],  # first 20 for logging
            "duration_seconds": duration_s,
        }

    # ──────────────────────────────────────────────
    # Chunk builders
    # ──────────────────────────────────────────────

    def _build_chunks(
        self, df: pd.DataFrame, source: str
    ) -> List[Dict[str, Any]]:
        """Convert a DataFrame into a list of chunk dicts."""
        columns = list(df.columns)
        chunks = []

        if self.chunk_strategy == "group" and self.group_column and self.group_column in df.columns:
            for group_val, group_df in df.groupby(self.group_column):
                chunk_id = str(uuid.uuid4())
                text = _group_to_text(group_df, self.group_column)
                chunks.append(
                    {
                        "id": chunk_id,
                        "text": text,
                        "metadata": {
                            "source": source,
                            "type": "csv_group",
                            "group_column": self.group_column,
                            "group_value": str(group_val),
                            "row_count": len(group_df),
                        },
                    }
                )
        else:
            # Row-level chunking
            for idx, row in df.iterrows():
                chunk_id = str(uuid.uuid4())
                text = _row_to_text_key_value(row, columns)
                if not text.strip():
                    continue
                chunks.append(
                    {
                        "id": chunk_id,
                        "text": text,
                        "metadata": {
                            "source": source,
                            "type": "csv_row",
                            "row_index": int(idx),
                            "columns": columns,
                        },
                    }
                )

        logger.info(f"Built {len(chunks)} chunks from {len(df)} rows | strategy={self.chunk_strategy}")
        return chunks
