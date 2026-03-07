"""
Week 5 - Unit tests for CSV Ingestor Cloud Function and CSVEmbedder.
"""

import io
import json
import pytest
from unittest.mock import MagicMock, patch, call


# ══════════════════════════════════════════════
# CSV Ingestor Cloud Function tests
# ══════════════════════════════════════════════

class TestCSVIngestorFunction:
    """Tests for the Cloud Function entry point."""

    @pytest.fixture
    def valid_csv_bytes(self):
        return b"name,age,department\nAlice,30,Engineering\nBob,25,Marketing\n"

    @pytest.fixture
    def mock_request_upload(self, valid_csv_bytes):
        """Simulate a multipart file upload request."""
        req = MagicMock()
        req.method = "POST"
        req.is_json = False
        uploaded_file = MagicMock()
        uploaded_file.read.return_value = valid_csv_bytes
        uploaded_file.filename = "test.csv"
        req.files = {"file": uploaded_file}
        return req

    @pytest.fixture
    def mock_request_gcs(self):
        """Simulate a JSON request with gcs_uri."""
        req = MagicMock()
        req.method = "POST"
        req.is_json = True
        req.files = {}
        req.get_json.return_value = {
            "gcs_uri": "gs://test-bucket/data.csv"
        }
        return req

    def test_options_returns_204(self):
        """OPTIONS pre-flight should return 204."""
        with patch("google.cloud.storage.Client"), \
             patch("google.cloud.pubsub_v1.PublisherClient"):
            from week5.cloud_functions.csv_ingestor.main import csv_ingestor
            req = MagicMock()
            req.method = "OPTIONS"
            resp, status, headers = csv_ingestor(req)
            assert status == 204
            assert "Access-Control-Allow-Origin" in headers

    def test_get_request_returns_405(self):
        """Non-POST requests should return 405."""
        with patch("google.cloud.storage.Client"), \
             patch("google.cloud.pubsub_v1.PublisherClient"):
            from week5.cloud_functions.csv_ingestor.main import csv_ingestor
            req = MagicMock()
            req.method = "GET"
            req.files = {}
            resp, status, _ = csv_ingestor(req)
            assert status == 405

    @patch("google.cloud.storage.Client")
    @patch("google.cloud.pubsub_v1.PublisherClient")
    def test_valid_csv_upload_returns_200(self, MockPubSub, MockStorage, valid_csv_bytes, mock_request_upload):
        """Valid CSV upload should return 200 with success status."""
        # Mock GCS upload
        mock_blob = MagicMock()
        MockStorage.return_value.bucket.return_value.blob.return_value = mock_blob

        # Mock Pub/Sub publish
        mock_future = MagicMock()
        mock_future.result.return_value = "msg-id-123"
        MockPubSub.return_value.publish.return_value = mock_future
        MockPubSub.return_value.topic_path.return_value = "projects/test/topics/csv"

        from week5.cloud_functions.csv_ingestor.main import csv_ingestor
        resp, status, _ = csv_ingestor(mock_request_upload)
        data = json.loads(resp)

        assert status == 200
        assert data["status"] == "success"
        assert "gcs_uri" in data
        assert data["validation"]["row_count"] == 2
        assert data["validation"]["column_count"] == 3

    @patch("google.cloud.storage.Client")
    @patch("google.cloud.pubsub_v1.PublisherClient")
    def test_invalid_csv_returns_422(self, MockPubSub, MockStorage):
        """Empty CSV should return 422 (unprocessable)."""
        req = MagicMock()
        req.method = "POST"
        req.is_json = False
        uploaded_file = MagicMock()
        uploaded_file.read.return_value = b""  # empty file
        uploaded_file.filename = "empty.csv"
        req.files = {"file": uploaded_file}

        from week5.cloud_functions.csv_ingestor.main import csv_ingestor
        resp, status, _ = csv_ingestor(req)
        data = json.loads(resp)
        assert status == 422
        assert data["status"] == "rejected"

    @patch("google.cloud.storage.Client")
    @patch("google.cloud.pubsub_v1.PublisherClient")
    def test_missing_file_and_gcs_uri_returns_400(self, MockPubSub, MockStorage):
        """Missing both file and gcs_uri should return 400."""
        req = MagicMock()
        req.method = "POST"
        req.is_json = True
        req.files = {}
        req.get_json.return_value = {}  # no gcs_uri

        from week5.cloud_functions.csv_ingestor.main import csv_ingestor
        resp, status, _ = csv_ingestor(req)
        assert status == 400


# ══════════════════════════════════════════════
# CSV Validation tests
# ══════════════════════════════════════════════

class TestCSVValidation:
    """Tests for the _validate_csv helper."""

    def test_valid_csv_passes(self):
        """A well-formed CSV should pass validation."""
        import pandas as pd
        from week5.cloud_functions.csv_ingestor.main import _validate_csv

        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        result = _validate_csv(df, "test.csv")
        assert result["valid"] is True
        assert result["row_count"] == 3

    def test_empty_csv_fails(self):
        """Empty DataFrame should fail validation."""
        import pandas as pd
        from week5.cloud_functions.csv_ingestor.main import _validate_csv

        df = pd.DataFrame()
        result = _validate_csv(df, "empty.csv")
        assert result["valid"] is False
        assert len(result["issues"]) > 0

    def test_high_null_columns_flagged(self):
        """Columns with >50% nulls should produce a warning issue."""
        import pandas as pd
        import numpy as np
        from week5.cloud_functions.csv_ingestor.main import _validate_csv

        df = pd.DataFrame({
            "good_col": [1, 2, 3, 4, 5],
            "mostly_null": [None, None, None, None, 5],
        })
        result = _validate_csv(df, "test.csv")
        # Should flag mostly_null column but still be valid (warning only)
        issues_text = " ".join(result["issues"])
        assert "mostly_null" in issues_text


# ══════════════════════════════════════════════
# CSVEmbedder tests
# ══════════════════════════════════════════════

class TestCSVEmbedder:
    """Tests for CSVEmbedder."""

    @pytest.fixture
    def sample_df_bytes(self):
        """Simple CSV bytes for embedding tests."""
        import pandas as pd
        df = pd.DataFrame({
            "product": ["Widget A", "Widget B", "Widget C"],
            "price": [10.99, 24.50, 5.00],
            "category": ["Hardware", "Software", "Hardware"],
        })
        return df.to_csv(index=False).encode()

    def test_row_to_text_key_value(self):
        """_row_to_text_key_value should format row as 'col: val | col: val'."""
        import pandas as pd
        from week5.rag.csv_embedder import _row_to_text_key_value

        row = pd.Series({"name": "Alice", "age": 30, "dept": "Eng"})
        text = _row_to_text_key_value(row, ["name", "age", "dept"])
        assert "name: Alice" in text
        assert "age: 30" in text
        assert "|" in text

    def test_row_to_text_skips_null(self):
        """_row_to_text_key_value should skip NaN values."""
        import pandas as pd
        import numpy as np
        from week5.rag.csv_embedder import _row_to_text_key_value

        row = pd.Series({"name": "Alice", "age": None, "dept": "Eng"})
        text = _row_to_text_key_value(row, ["name", "age", "dept"])
        assert "age" not in text

    @patch("google.cloud.storage.Client")
    def test_build_chunks_row_strategy(self, MockStorage, sample_df_bytes):
        """_build_chunks with 'row' strategy should produce one chunk per row."""
        import pandas as pd

        with patch("vertexai.init"):
            from week5.rag.csv_embedder import CSVEmbedder
            embedder = CSVEmbedder.__new__(CSVEmbedder)
            embedder.chunk_strategy = "row"
            embedder.group_column = None
            embedder._gcs_client = MockStorage.return_value

            df = pd.read_csv(io.BytesIO(sample_df_bytes))
            chunks = embedder._build_chunks(df, "test_source")

        assert len(chunks) == 3  # one per row
        for c in chunks:
            assert "id" in c
            assert "text" in c
            assert "metadata" in c
            assert c["metadata"]["type"] == "csv_row"

    @patch("google.cloud.storage.Client")
    def test_build_chunks_group_strategy(self, MockStorage, sample_df_bytes):
        """_build_chunks with 'group' strategy should produce one chunk per group."""
        import pandas as pd

        with patch("vertexai.init"):
            from week5.rag.csv_embedder import CSVEmbedder
            embedder = CSVEmbedder.__new__(CSVEmbedder)
            embedder.chunk_strategy = "group"
            embedder.group_column = "category"
            embedder._gcs_client = MockStorage.return_value

            df = pd.read_csv(io.BytesIO(sample_df_bytes))
            chunks = embedder._build_chunks(df, "test_source")

        # "Hardware" and "Software" → 2 groups
        assert len(chunks) == 2
        categories_in_chunks = [c["metadata"]["group_value"] for c in chunks]
        assert "Hardware" in categories_in_chunks
        assert "Software" in categories_in_chunks
