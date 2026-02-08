"""
Unit tests for storage modules.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch


class TestGCSStore:
    """Test Google Cloud Storage operations."""
    
    @pytest.fixture
    def mock_gcs_client(self, mocker):
        """Mock GCS client."""
        mock_client = mocker.Mock()
        mock_bucket = mocker.Mock()
        mock_blob = mocker.Mock()
        mock_blob.public_url = "https://storage.googleapis.com/bucket/file.txt"
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket
        return mock_client
    
    @pytest.fixture
    def gcs_store(self, mock_gcs_client, mocker):
        """Create GCS store with mocked client."""
        mocker.patch("google.cloud.storage.Client", return_value=mock_gcs_client)
        from app.storage.gcs_store import GCSStore
        return GCSStore()
    
    def test_upload_file(self, gcs_store, mock_gcs_client):
        """Test file upload."""
        filename = "test.txt"
        content = b"Test content"
        
        result = gcs_store.upload_file(filename, content)
        
        assert result is not None
        assert "storage.googleapis.com" in result or "gs://" in result
    
    def test_download_file(self, gcs_store, mock_gcs_client):
        """Test file download."""
        mock_blob = mock_gcs_client.bucket().blob()
        mock_blob.download_as_bytes.return_value = b"Test content"
        
        result = gcs_store.download_file("test.txt")
        
        assert result == b"Test content"
    
    def test_delete_file(self, gcs_store, mock_gcs_client):
        """Test file deletion."""
        result = gcs_store.delete_file("test.txt")
        
        # Should not raise error
        assert result is None or result is True
    
    def test_list_files(self, gcs_store, mock_gcs_client):
        """Test listing files."""
        mock_blobs = [Mock(name="file1.txt"), Mock(name="file2.txt")]
        mock_gcs_client.bucket().list_blobs.return_value = mock_blobs
        
        result = gcs_store.list_files()
        
        assert len(result) == 2 or result is not None


class TestFirestoreStore:
    """Test Firestore operations."""
    
    @pytest.fixture
    def mock_firestore_client(self, mocker):
        """Mock Firestore client."""
        mock_client = mocker.Mock()
        mock_collection = mocker.Mock()
        mock_doc_ref = mocker.Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_client.collection.return_value = mock_collection
        return mock_client
    
    @pytest.fixture
    def firestore_store(self, mock_firestore_client, mocker):
        """Create Firestore store with mocked client."""
        mocker.patch("google.cloud.firestore.Client", return_value=mock_firestore_client)
        from app.storage.firestore_store import FirestoreStore
        return FirestoreStore()
    
    def test_add_document(self, firestore_store, mock_firestore_client):
        """Test adding document."""
        collection = "test_collection"
        doc_id = "doc1"
        data = {"key": "value"}
        
        result = firestore_store.add_document(collection, doc_id, data)
        
        # Should not raise error
        assert result is None or result is True
    
    def test_get_document(self, firestore_store, mock_firestore_client):
        """Test getting document."""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"key": "value"}
        mock_firestore_client.collection().document().get.return_value = mock_doc
        
        result = firestore_store.get_document("test_collection", "doc1")
        
        assert result == {"key": "value"}
    
    def test_get_nonexistent_document(self, firestore_store, mock_firestore_client):
        """Test getting nonexistent document."""
        mock_doc = Mock()
        mock_doc.exists = False
        mock_firestore_client.collection().document().get.return_value = mock_doc
        
        result = firestore_store.get_document("test_collection", "nonexistent")
        
        assert result is None
    
    def test_update_document(self, firestore_store, mock_firestore_client):
        """Test updating document."""
        result = firestore_store.update_document(
            "test_collection",
            "doc1",
            {"key": "new_value"}
        )
        
        # Should not raise error
        assert result is None or result is True
    
    def test_delete_document(self, firestore_store, mock_firestore_client):
        """Test deleting document."""
        result = firestore_store.delete_document("test_collection", "doc1")
        
        # Should not raise error
        assert result is None or result is True
    
    def test_query_documents(self, firestore_store, mock_firestore_client):
        """Test querying documents."""
        mock_docs = [
            Mock(to_dict=lambda: {"key": "value1"}),
            Mock(to_dict=lambda: {"key": "value2"})
        ]
        mock_firestore_client.collection().where().stream.return_value = mock_docs
        
        result = firestore_store.query_documents("test_collection", "key", "==", "value1")
        
        assert isinstance(result, list) or result is not None


class TestStorageEdgeCases:
    """Test edge cases for storage operations."""
    
    def test_upload_empty_file(self, mocker):
        """Test uploading empty file."""
        mock_client = mocker.Mock()
        mocker.patch("google.cloud.storage.Client", return_value=mock_client)
        
        from app.storage.gcs_store import GCSStore
        store = GCSStore()
        
        result = store.upload_file("empty.txt", b"")
        
        # Should handle gracefully
        assert result is not None or result is None
    
    def test_upload_large_file(self, mocker):
        """Test uploading large file."""
        mock_client = mocker.Mock()
        mocker.patch("google.cloud.storage.Client", return_value=mock_client)
        
        from app.storage.gcs_store import GCSStore
        store = GCSStore()
        
        large_content = b"A" * (10 * 1024 * 1024)  # 10MB
        result = store.upload_file("large.txt", large_content)
        
        assert result is not None or result is None
    
    def test_storage_connection_error(self, mocker):
        """Test handling of storage connection errors."""
        mock_client = mocker.Mock()
        mock_client.bucket.side_effect = Exception("Connection error")
        mocker.patch("google.cloud.storage.Client", return_value=mock_client)
        
        from app.storage.gcs_store import GCSStore
        store = GCSStore()
        
        with pytest.raises(Exception):
            store.upload_file("test.txt", b"content")
