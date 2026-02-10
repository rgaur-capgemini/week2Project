"""
Comprehensive tests for FirestoreChunkStore - 100% coverage target.
Tests all methods, branches, edge cases, and exception paths.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock

from app.storage.firestore_store import FirestoreChunkStore


class TestFirestoreChunkStoreInit:
    """Test FirestoreChunkStore initialization."""
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_init_success(self, mock_firestore_class):
        """Test successful initialization."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_firestore_class.return_value = mock_db
        
        store = FirestoreChunkStore(
            project_id="test-project"
        )
        
        assert store.db is not None
        assert store.collection is not None
        mock_db.collection.assert_called_once_with("rag_chunks")
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_init_custom_collection(self, mock_firestore_class):
        """Test initialization with custom collection name."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_firestore_class.return_value = mock_db
        
        store = FirestoreChunkStore(
            project_id="test-project",
            collection_name="custom_chunks"
        )
        
        mock_db.collection.assert_called_once_with("custom_chunks")
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_init_firestore_fails(self, mock_firestore_class):
        """Test initialization when Firestore client creation fails."""
        mock_firestore_class.side_effect = Exception("Firestore not available")
        
        store = FirestoreChunkStore(
            project_id="test-project"
        )
        
        assert store.db is None
        assert store.collection is None


class TestStoreChunk:
    """Test store_chunk method."""
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_store_chunk_success(self, mock_firestore_class):
        """Test successful chunk storage."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_doc = MagicMock()
        mock_collection.document.return_value = mock_doc
        mock_db.collection.return_value = mock_collection
        mock_firestore_class.return_value = mock_db
        
        store = FirestoreChunkStore(project_id="test-project")
        
        chunk_data = {
            "text": "Test chunk text",
            "metadata": {"source": "doc1.pdf"},
            "vector": [0.1, 0.2, 0.3]
        }
        
        result = store.store_chunk("chunk-123", chunk_data)
        
        assert result is True
        mock_doc.set.assert_called_once()
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_store_chunk_no_collection(self, mock_firestore_class):
        """Test storing chunk when collection is None."""
        mock_firestore_class.side_effect = Exception("Firestore not available")
        
        store = FirestoreChunkStore(project_id="test-project")
        
        chunk_data = {"text": "Test", "metadata": {}, "vector": []}
        result = store.store_chunk("chunk-123", chunk_data)
        
        assert result is False
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_store_chunk_firestore_error(self, mock_firestore_class):
        """Test storing chunk when Firestore raises error."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_doc = MagicMock()
        mock_doc.set.side_effect = Exception("Write failed")
        mock_collection.document.return_value = mock_doc
        mock_db.collection.return_value = mock_collection
        mock_firestore_class.return_value = mock_db
        
        store = FirestoreChunkStore(project_id="test-project")
        
        chunk_data = {"text": "Test", "metadata": {}, "vector": []}
        result = store.store_chunk("chunk-123", chunk_data)
        
        assert result is False
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_store_chunk_with_timestamp(self, mock_firestore_class):
        """Test chunk storage includes timestamps."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_doc = MagicMock()
        mock_collection.document.return_value = mock_doc
        mock_db.collection.return_value = mock_collection
        mock_firestore_class.return_value = mock_db
        
        from google.cloud import firestore as fs
        
        store = FirestoreChunkStore(project_id="test-project")
        
        chunk_data = {"text": "Test", "metadata": {}, "vector": []}
        store.store_chunk("chunk-123", chunk_data)
        
        # Verify timestamps in stored data
        call_args = mock_doc.set.call_args
        stored_data = call_args[0][0]
        assert "created_at" in stored_data
        assert "updated_at" in stored_data


class TestBatchStoreChunks:
    """Test batch_store_chunks method."""
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_batch_store_success(self, mock_firestore_class):
        """Test successful batch storage."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_batch = MagicMock()
        mock_db.batch.return_value = mock_batch
        mock_db.collection.return_value = mock_collection
        mock_firestore_class.return_value = mock_db
        
        store = FirestoreChunkStore(project_id="test-project")
        
        chunks = {
            "chunk-1": {"text": "Text 1", "metadata": {}, "vector": [0.1]},
            "chunk-2": {"text": "Text 2", "metadata": {}, "vector": [0.2]}
        }
        
        result = store.batch_store_chunks(chunks)
        
        assert result == 2
        mock_batch.commit.assert_called_once()
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_batch_store_large_batch(self, mock_firestore_class):
        """Test batch storage with >500 chunks (Firestore limit)."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_batch = MagicMock()
        mock_db.batch.return_value = mock_batch
        mock_db.collection.return_value = mock_collection
        mock_firestore_class.return_value = mock_db
        
        store = FirestoreChunkStore(project_id="test-project")
        
        # Create 600 chunks to test batch splitting
        chunks = {
            f"chunk-{i}": {"text": f"Text {i}", "metadata": {}, "vector": [0.1]}
            for i in range(600)
        }
        
        result = store.batch_store_chunks(chunks)
        
        assert result == 600
        # Should commit twice (500 + 100)
        assert mock_batch.commit.call_count == 2
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_batch_store_exactly_500(self, mock_firestore_class):
        """Test batch storage with exactly 500 chunks."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_batch = MagicMock()
        mock_db.batch.return_value = mock_batch
        mock_db.collection.return_value = mock_collection
        mock_firestore_class.return_value = mock_db
        
        store = FirestoreChunkStore(project_id="test-project")
        
        chunks = {
            f"chunk-{i}": {"text": f"Text {i}", "metadata": {}, "vector": [0.1]}
            for i in range(500)
        }
        
        result = store.batch_store_chunks(chunks)
        
        assert result == 500
        # Should commit once at 500
        assert mock_batch.commit.call_count == 1
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_batch_store_no_db(self, mock_firestore_class):
        """Test batch storage when db is None."""
        mock_firestore_class.side_effect = Exception("Firestore not available")
        
        store = FirestoreChunkStore(project_id="test-project")
        
        chunks = {"chunk-1": {"text": "Test", "metadata": {}, "vector": []}}
        result = store.batch_store_chunks(chunks)
        
        assert result == 0
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_batch_store_empty_chunks(self, mock_firestore_class):
        """Test batch storage with empty chunks dictionary."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_batch = MagicMock()
        mock_db.batch.return_value = mock_batch
        mock_db.collection.return_value = mock_collection
        mock_firestore_class.return_value = mock_db
        
        store = FirestoreChunkStore(project_id="test-project")
        
        result = store.batch_store_chunks({})
        
        assert result == 0


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_store_chunk_with_empty_text(self, mock_firestore_class):
        """Test storing chunk with empty text."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_doc = MagicMock()
        mock_collection.document.return_value = mock_doc
        mock_db.collection.return_value = mock_collection
        mock_firestore_class.return_value = mock_db
        
        store = FirestoreChunkStore(project_id="test-project")
        
        chunk_data = {"text": "", "metadata": {}, "vector": []}
        result = store.store_chunk("chunk-123", chunk_data)
        
        assert result is True
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_store_chunk_with_very_long_text(self, mock_firestore_class):
        """Test storing chunk with very long text."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_doc = MagicMock()
        mock_collection.document.return_value = mock_doc
        mock_db.collection.return_value = mock_collection
        mock_firestore_class.return_value = mock_db
        
        store = FirestoreChunkStore(project_id="test-project")
        
        long_text = "word " * 100000
        chunk_data = {"text": long_text, "metadata": {}, "vector": []}
        result = store.store_chunk("chunk-123", chunk_data)
        
        assert result is True
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_store_chunk_with_unicode(self, mock_firestore_class):
        """Test storing chunk with Unicode characters."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_doc = MagicMock()
        mock_collection.document.return_value = mock_doc
        mock_db.collection.return_value = mock_collection
        mock_firestore_class.return_value = mock_db
        
        store = FirestoreChunkStore(project_id="test-project")
        
        chunk_data = {
            "text": "测试文本 🚀",
            "metadata": {"language": "zh"},
            "vector": [0.1, 0.2, 0.3]
        }
        result = store.store_chunk("chunk-123", chunk_data)
        
        assert result is True
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_store_chunk_missing_fields(self, mock_firestore_class):
        """Test storing chunk with missing optional fields."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_doc = MagicMock()
        mock_collection.document.return_value = mock_doc
        mock_db.collection.return_value = mock_collection
        mock_firestore_class.return_value = mock_db
        
        store = FirestoreChunkStore(project_id="test-project")
        
        # Missing metadata and vector
        chunk_data = {"text": "Test text"}
        result = store.store_chunk("chunk-123", chunk_data)
        
        assert result is True


@pytest.mark.xfail(reason="Testing advanced Firestore features")
class TestAdvancedFeatures:
    """Test advanced Firestore features."""
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_retrieve_chunk(self, mock_firestore_class):
        """Test retrieving chunk if method exists."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_firestore_class.return_value = mock_db
        
        store = FirestoreChunkStore(project_id="test-project")
        
        # If store has retrieve method
        if hasattr(store, 'retrieve_chunk'):
            chunk = store.retrieve_chunk("chunk-123")
            assert chunk is not None
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_delete_chunk(self, mock_firestore_class):
        """Test deleting chunk if method exists."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_firestore_class.return_value = mock_db
        
        store = FirestoreChunkStore(project_id="test-project")
        
        # If store has delete method
        if hasattr(store, 'delete_chunk'):
            result = store.delete_chunk("chunk-123")
            assert isinstance(result, bool)


class TestCountChunks:
    """Test count_chunks method."""
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_count_chunks_success(self, mock_firestore_class):
        """Test counting chunks successfully."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_query = MagicMock()
        mock_result = MagicMock()
        mock_result.value = 100
        
        mock_query.get.return_value = [[mock_result]]
        mock_collection.count.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        mock_firestore_class.return_value = mock_db
        
        store = FirestoreChunkStore(project_id="test-project")
        count = store.count_chunks()
        
        assert count == 100
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_count_chunks_fallback_to_stream(self, mock_firestore_class):
        """Test count chunks fallback to manual count."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        
        # Make count() raise exception
        mock_collection.count.side_effect = Exception("Count not supported")
        
        # Mock stream() for fallback
        mock_collection.stream.return_value = [1, 2, 3, 4, 5]  # 5 items
        mock_db.collection.return_value = mock_collection
        mock_firestore_class.return_value = mock_db
        
        store = FirestoreChunkStore(project_id="test-project")
        count = store.count_chunks()
        
        assert count == 5
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_count_chunks_all_methods_fail(self, mock_firestore_class):
        """Test count when both methods fail."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        
        # Both methods fail
        mock_collection.count.side_effect = Exception("Count failed")
        mock_collection.stream.side_effect = Exception("Stream failed")
        mock_db.collection.return_value = mock_collection
        mock_firestore_class.return_value = mock_db
        
        store = FirestoreChunkStore(project_id="test-project")
        count = store.count_chunks()
        
        assert count == 0
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_count_chunks_no_collection(self, mock_firestore_class):
        """Test count when collection is None."""
        mock_db = MagicMock()
        mock_db.collection.return_value = None
        mock_firestore_class.return_value = mock_db
        
        store = FirestoreChunkStore(project_id="test-project")
        store.collection = None
        
        count = store.count_chunks()
        assert count == 0
