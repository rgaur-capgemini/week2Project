"""
Week 5 - Cloud Function: CSV Ingestor

Trigger: HTTP POST  (can also be wired to a GCS Pub/Sub trigger)

Responsibilities:
  1. Accept CSV file upload or a GCS URI pointing to an existing CSV.
  2. Validate the CSV (schema, encoding, size).
  3. Upload/copy the raw CSV to the designated GCS bucket.
  4. Publish a Pub/Sub message so the embedding pipeline picks it up.
  5. Return a structured JSON response with ingestion status.

Deploy command:
  gcloud functions deploy csv-ingestor \
    --gen2 \
    --runtime=python311 \
    --region=us-central1 \
    --source=. \
    --entry-point=csv_ingestor \
    --trigger-http \
    --allow-unauthenticated \
    --set-env-vars PROJECT_ID=<project>,GCS_CSV_BUCKET=<bucket>,PUBSUB_TOPIC=csv-ingestion-topic
"""

import io
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, Optional

import functions_framework
import pandas as pd
from flask import Request
from google.cloud import pubsub_v1, storage

# ──────────────────────────────────────────────
# Configuration from environment
# ──────────────────────────────────────────────
PROJECT_ID = os.environ.get("PROJECT_ID", "botpproject")
GCS_CSV_BUCKET = os.environ.get("GCS_CSV_BUCKET", f"{PROJECT_ID}-csv-data")
PUBSUB_TOPIC = os.environ.get("PUBSUB_TOPIC", "csv-ingestion-topic")
MAX_CSV_SIZE_BYTES = int(os.environ.get("MAX_CSV_SIZE_MB", "50")) * 1024 * 1024
MAX_ROWS = int(os.environ.get("MAX_CSV_ROWS", "100000"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GCP clients (initialised once per cold start)
_storage_client: Optional[storage.Client] = None
_pubsub_publisher: Optional[pubsub_v1.PublisherClient] = None


def _get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client


def _get_pubsub_publisher() -> pubsub_v1.PublisherClient:
    global _pubsub_publisher
    if _pubsub_publisher is None:
        _pubsub_publisher = pubsub_v1.PublisherClient()
    return _pubsub_publisher


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _validate_csv(df: pd.DataFrame, filename: str) -> Dict[str, Any]:
    """Validate a parsed DataFrame and return a validation report."""
    issues = []

    if len(df) == 0:
        issues.append("CSV has no rows.")
    if len(df.columns) == 0:
        issues.append("CSV has no columns.")
    if len(df) > MAX_ROWS:
        issues.append(f"CSV exceeds max row limit ({MAX_ROWS}). Found {len(df)}.")

    # Warn about columns with >50% null values
    high_null_cols = [
        col for col in df.columns if df[col].isnull().mean() > 0.5
    ]
    if high_null_cols:
        issues.append(f"Columns with >50% nulls: {high_null_cols}")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "null_counts": df.isnull().sum().to_dict(),
        "file": filename,
    }


def _upload_to_gcs(
    csv_bytes: bytes,
    filename: str,
    metadata: Optional[Dict] = None,
) -> str:
    """Upload raw CSV bytes to GCS and return the gs:// URI."""
    client = _get_storage_client()
    bucket = client.bucket(GCS_CSV_BUCKET)

    # Use a timestamped path to avoid collisions
    ts = time.strftime("%Y/%m/%d")
    blob_name = f"csv-ingest/{ts}/{filename}"
    blob = bucket.blob(blob_name)

    if metadata:
        blob.metadata = metadata

    blob.upload_from_string(csv_bytes, content_type="text/csv")
    gcs_uri = f"gs://{GCS_CSV_BUCKET}/{blob_name}"
    logger.info(f"Uploaded CSV to {gcs_uri}")
    return gcs_uri


def _publish_ingestion_event(
    gcs_uri: str,
    validation: Dict,
    ingestion_id: str,
) -> str:
    """Publish a Pub/Sub message to trigger the embedding pipeline."""
    publisher = _get_pubsub_publisher()
    topic_path = publisher.topic_path(PROJECT_ID, PUBSUB_TOPIC)

    message = {
        "ingestion_id": ingestion_id,
        "gcs_uri": gcs_uri,
        "row_count": validation["row_count"],
        "columns": validation["columns"],
        "timestamp": time.time(),
        "status": "pending_embedding",
    }

    future = publisher.publish(
        topic_path,
        data=json.dumps(message).encode("utf-8"),
        ingestion_id=ingestion_id,
    )
    message_id = future.result(timeout=10)
    logger.info(f"Published Pub/Sub message: {message_id}")
    return message_id


# ──────────────────────────────────────────────
# Cloud Function entry point
# ──────────────────────────────────────────────

@functions_framework.http
def csv_ingestor(request: Request):
    """
    HTTP Cloud Function – ingest a CSV into GCS and trigger embedding.

    Accepts:
      - Multipart form-data with a 'file' field (CSV upload)
      - JSON body with 'gcs_uri' field (existing GCS CSV)

    Returns JSON with ingestion result.
    """
    ingestion_id = str(uuid.uuid4())
    start_time = time.time()

    logger.info(f"CSV ingestion request | id={ingestion_id} | method={request.method}")

    # ── CORS pre-flight ─────────────────────────
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }
        return ("", 204, headers)

    cors_headers = {"Access-Control-Allow-Origin": "*"}

    if request.method != "POST":
        return (
            json.dumps({"error": "Only POST method is supported."}),
            405,
            cors_headers,
        )

    csv_bytes: Optional[bytes] = None
    filename = f"upload_{ingestion_id}.csv"

    try:
        # ── Case 1: File upload via multipart form ─
        if request.files and "file" in request.files:
            uploaded = request.files["file"]
            csv_bytes = uploaded.read()
            filename = uploaded.filename or filename

            if len(csv_bytes) > MAX_CSV_SIZE_BYTES:
                return (
                    json.dumps({"error": f"File exceeds {MAX_CSV_SIZE_BYTES // (1024*1024)} MB limit."}),
                    413,
                    cors_headers,
                )

        # ── Case 2: JSON body with gcs_uri ─────────
        elif request.is_json:
            body = request.get_json()
            gcs_uri_input = body.get("gcs_uri")

            if not gcs_uri_input:
                return (
                    json.dumps({"error": "Provide 'file' in form-data or 'gcs_uri' in JSON body."}),
                    400,
                    cors_headers,
                )

            # Download from GCS
            path = gcs_uri_input.replace("gs://", "")
            bucket_name, blob_name = path.split("/", 1)
            client = _get_storage_client()
            blob = client.bucket(bucket_name).blob(blob_name)
            csv_bytes = blob.download_as_bytes()
            filename = blob_name.split("/")[-1]

        else:
            return (
                json.dumps({"error": "Unsupported content-type. Use multipart/form-data or application/json."}),
                415,
                cors_headers,
            )

        # ── Parse & validate ───────────────────────
        df = pd.read_csv(io.BytesIO(csv_bytes))
        validation = _validate_csv(df, filename)

        if not validation["valid"]:
            return (
                json.dumps(
                    {
                        "ingestion_id": ingestion_id,
                        "status": "rejected",
                        "validation": validation,
                    }
                ),
                422,
                cors_headers,
            )

        # ── Upload to GCS ──────────────────────────
        gcs_uri = _upload_to_gcs(
            csv_bytes=csv_bytes,
            filename=filename,
            metadata={"ingestion_id": ingestion_id, "rows": str(validation["row_count"])},
        )

        # ── Publish Pub/Sub event ──────────────────
        try:
            pubsub_message_id = _publish_ingestion_event(gcs_uri, validation, ingestion_id)
        except Exception as pub_err:
            logger.warning(f"Pub/Sub publish failed (non-fatal): {pub_err}")
            pubsub_message_id = None

        duration_ms = int((time.time() - start_time) * 1000)

        response_body = {
            "ingestion_id": ingestion_id,
            "status": "success",
            "gcs_uri": gcs_uri,
            "validation": validation,
            "pubsub_message_id": pubsub_message_id,
            "duration_ms": duration_ms,
        }

        logger.info(f"CSV ingestion complete | id={ingestion_id} | uri={gcs_uri} | ms={duration_ms}")
        return (json.dumps(response_body), 200, cors_headers)

    except pd.errors.ParserError as pe:
        logger.error(f"CSV parse error: {pe}")
        return (
            json.dumps({"ingestion_id": ingestion_id, "status": "error", "error": f"Invalid CSV: {pe}"}),
            400,
            cors_headers,
        )
    except Exception as exc:
        logger.error(f"Ingestion failed: {exc}")
        return (
            json.dumps({"ingestion_id": ingestion_id, "status": "error", "error": str(exc)}),
            500,
            cors_headers,
        )
