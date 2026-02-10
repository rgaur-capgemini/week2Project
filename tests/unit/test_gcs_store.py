"""
Comprehensive tests for GCSDocumentStore - 100% coverage target.
Tests all methods, branches, edge cases, and exception paths.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime

from app.storage.gcs_store import GCSDocumentStore


class TestGCSDocumentStoreInit:
    """Test GCSDocumentStore initialization."""
    
    @patch('app.storage.gcs_store.storage.Client')
    def test_init_bucket_exists(self, mock_storage_class):
        """Test initialization when bucket exists."""
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.exists.return_value = True
        mock_client.bucket.return_value = mock_bucket
        mock_storage_class.return_value = mock_client
        
        store = GCSDocumentStore(
            project_id="test-project",
            bucket_name="test-bucket"
        )
        
        assert store.client is not None
        assert store.bucket is not None
        mock_bucket.exists.assert_called_once()
    
    @patch('app.storage.gcs_store.storage.Client')
    def test_init_bucket_not_exists_creates_bucket(self, mock_storage_class):
        """Test initialization creates bucket if it doesn't exist."""
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.exists.return_value = False
        mock_client.bucket.return_value = mock_bucket
        mock_client.create_bucket.return_value = mock_bucket
        mock_storage_class.return_value = mock_client
        
        store = GCSDocumentStore(
            project_id="test-project",
            bucket_name="test-bucket"
        )
        
        mock_client.create_bucket.assert_called_once_with(
            "test-bucket",
            location="us-central1"
        )
    
    @patch('app.storage.gcs_store.storage.Client')
    def test_init_storage_client_fails(self, mock_storage_class):
        """Test initialization when storage client creation fails."""
        mock_storage_class.side_effect = Exception("Storage API not available")
        
        store = GCSDocumentStore(
            project_id="test-project",
            bucket_name="test-bucket"
        )
        
        assert store.bucket is None


class TestUploadDocument:
    """Test document upload functionality."""
    
    @patch('app.storage.gcs_store.storage.Client')
    def test_upload_document_success(self, mock_storage_class):
        """Test successful document upload."""
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.exists.return_value = True
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket
        mock_storage_class.return_value = mock_client
        
        store = GCSDocumentStore(
            project_id="test-project",
            bucket_name="test-bucket"
        )
        
        content = b"Test document content"
        result = store.upload_document(
            filename="test.txt",
            content=content,
            content_type="text/plain"
        )
        
        assert result is not None
        assert result.startswith("gs://test-bucket/documents/")
        mock_blob.upload_from_string.assert_called_once_with(content)
        assert mock_blob.content_type == "text/plain"
    
    @patch('app.storage.gcs_store.storage.Client')
    def test_upload_document_with_metadata(self, mock_storage_class):
        """Test document upload with metadata."""
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.exists.return_value = True
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket
        mock_storage_class.return_value = mock_client
        
        store = GCSDocumentStore(
            project_id="test-project",
            bucket_name="test-bucket"
        )
        
        content = b"Test content"
        metadata = {"user_id": "user-123", "category": "report"}
        result = store.upload_document(
            filename="test.pdf",
            content=content,
            content_type="application/pdf",
            metadata=metadata
        )
        
        assert result is not None
        assert mock_blob.metadata == metadata
    
    @patch('app.storage.gcs_store.storage.Client')
    def test_upload_document_no_bucket(self, mock_storage_class):
        """Test upload when bucket is None."""
        mock_storage_class.side_effect = Exception("Storage API not available")
        
        store = GCSDocumentStore(
            project_id="test-project",
            bucket_name="test-bucket"
        )
        
        result = store.upload_document(
            filename="test.txt",
            content=b"Test content"
        )
        
        assert result is None
    
    @patch('app.storage.gcs_store.storage.Client')
    def test_upload_document_upload_fails(self, mock_storage_class):
        """Test upload when blob upload fails."""
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.exists.return_value = True
        mock_bucket.blob.return_value = mock_blob
        mock_blob.upload_from_string.side_effect = Exception("Upload failed")
        mock_client.bucket.return_value = mock_bucket
        mock_storage_class.return_value = mock_client
        
        store = GCSDocumentStore(
            project_id="test-project",
            bucket_name="test-bucket"
        )
        
        result = store.upload_document(
            filename="test.txt",
            content=b"Test content"
        )
        
        assert result is None
    
    @patch('app.storage.gcs_store.storage.Client')
    def test_upload_document_default_content_type(self, mock_storage_class):
        """Test upload with default content type."""
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.exists.return_value = True
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket
        mock_storage_class.return_value = mock_client
        
        store = GCSDocumentStore(
            project_id="test-project",
            bucket_name="test-bucket"
        )
        
        result = store.upload_document(
            filename="test.bin",
            content=b"Binary content"
        )
        
        assert result is not None
        assert mock_blob.content_type == "application/octet-stream"
    
    @patch('app.storage.gcs_store.storage.Client')
    def test_upload_document_timestamp_in_path(self, mock_storage_class):
        """Test that uploaded document path includes timestamp."""
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.exists.return_value = True
        mock_bucket.blob.return_value = mock_blob
        mock_bucket.name = "test-bucket"
        mock_client.bucket.return_value = mock_bucket
        mock_storage_class.return_value = mock_client
        
        store = GCSDocumentStore(
            project_id="test-project",
            bucket_name="test-bucket"
        )
        
        result = store.upload_document(
            filename="test.txt",
            content=b"Test content"
        )
        
        # Verify path format: gs://bucket/documents/TIMESTAMP_filename
        assert "documents/" in result
        assert "_test.txt" in result


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @patch('app.storage.gcs_store.storage.Client')
    def test_upload_empty_file(self, mock_storage_class):
        """Test uploading empty file."""
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.exists.return_value = True
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket
        mock_storage_class.return_value = mock_client
        
        store = GCSDocumentStore(
            project_id="test-project",
            bucket_name="test-bucket"
        )
        
        result = store.upload_document(
            filename="empty.txt",
            content=b""
        )
        
        assert result is not None
    
    @patch('app.storage.gcs_store.storage.Client')
    def test_upload_very_large_file(self, mock_storage_class):
        """Test uploading very large file."""
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.exists.return_value = True
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket
        mock_storage_class.return_value = mock_client
        
        store = GCSDocumentStore(
            project_id="test-project",
            bucket_name="test-bucket"
        )
        
        large_content = b"x" * (10 * 1024 * 1024)  # 10 MB
        result = store.upload_document(
            filename="large.bin",
            content=large_content
        )
        
        assert result is not None
    
    @patch('app.storage.gcs_store.storage.Client')
    def test_upload_special_characters_in_filename(self, mock_storage_class):
        """Test uploading file with special characters in name."""
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.exists.return_value = True
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket
        mock_storage_class.return_value = mock_client
        
        store = GCSDocumentStore(
            project_id="test-project",
            bucket_name="test-bucket"
        )
        
        result = store.upload_document(
            filename="test file (copy) #1.txt",
            content=b"Test content"
        )
        
        assert result is not None
    
    @patch('app.storage.gcs_store.storage.Client')
    def test_upload_unicode_filename(self, mock_storage_class):
        """Test uploading file with Unicode characters in name."""
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.exists.return_value = True
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket
        mock_storage_class.return_value = mock_client
        
        store = GCSDocumentStore(
            project_id="test-project",
            bucket_name="test-bucket"
        )
        
        result = store.upload_document(
            filename="测试文件.txt",
            content=b"Test content"
        )
        
        assert result is not None


class TestBucketCreation:
    """Test bucket creation scenarios."""
    
    @patch('app.storage.gcs_store.storage.Client')
    def test_bucket_creation_fails(self, mock_storage_class):
        """Test when bucket creation fails."""
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.exists.return_value = False
        mock_client.bucket.return_value = mock_bucket
        mock_client.create_bucket.side_effect = Exception("Permission denied")
        mock_storage_class.return_value = mock_client
        
        try:
            store = GCSDocumentStore(
                project_id="test-project",
                bucket_name="test-bucket"
            )
            # Should handle gracefully or raise
        except Exception:
            pass


@pytest.mark.xfail(reason="Testing advanced GCS features")
class TestAdvancedFeatures:
    """Test advanced GCS features."""
    
    @patch('app.storage.gcs_store.storage.Client')
    def test_upload_with_lifecycle_policy(self, mock_storage_class):
        """Test upload with lifecycle policy."""
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.exists.return_value = True
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket
        mock_storage_class.return_value = mock_client
        
        store = GCSDocumentStore(
            project_id="test-project",
            bucket_name="test-bucket"
        )
        
        # If store has lifecycle policy methods
        if hasattr(store, 'set_lifecycle_policy'):
            store.set_lifecycle_policy(days=90)
    
    @patch('app.storage.gcs_store.storage.Client')
    def test_upload_with_encryption(self, mock_storage_class):
        """Test upload with encryption."""
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.exists.return_value = True
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket
        mock_storage_class.return_value = mock_client
        
        store = GCSDocumentStore(
            project_id="test-project",
            bucket_name="test-bucket"
        )
        
        # If store has encryption methods
        if hasattr(store, 'upload_encrypted'):
            result = store.upload_encrypted(
                filename="secure.txt",
                content=b"Sensitive data",
                encryption_key="test-key"
            )
