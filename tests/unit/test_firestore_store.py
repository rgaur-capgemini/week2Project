"""
Comprehensive unit tests for Firestore storage.
Tests document operations, batch operations, and error handling.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from google.cloud import firestore

from app.storage.firestore_store import FirestoreChunkStore


class TestFirestoreChunkStoreInit:
    """Test Firestore store initialization."""
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_init_success(self, mock_client):
        """Test successful initialization."""
        mock_db = MagicMock()
        mock_client.return_value = mock_db
        
        store = FirestoreChunkStore(
            project_id="test-project",
            collection_name="test_chunks"
        )
        
        assert store.db == mock_db
        assert store.collection is not None
        mock_client.assert_called_once_with(project="test-project")
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_init_default_collection(self, mock_client):
        """Test initialization with default collection name."""
        mock_db = MagicMock()
        mock_client.return_value = mock_db
        
        store = FirestoreChunkStore(project_id="test-project")
        
        # Should use default collection name
        mock_db.collection.assert_called_with("rag_chunks")
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_init_failure(self, mock_client):
        """Test initialization failure handling."""
        mock_client.side_effect = Exception("Firestore connection error")
        
        store = FirestoreChunkStore(project_id="test-project")
        
        assert store.db is None
        assert store.collection is None
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_init_custom_collection(self, mock_client):
        """Test initialization with custom collection name."""
        mock_db = MagicMock()
        mock_client.return_value = mock_db
        
        store = FirestoreChunkStore(
            project_id="test-project",
            collection_name="custom_collection"
        )
        
        mock_db.collection.assert_called_with("custom_collection")


class TestFirestoreChunkStoreStoreChunk:
    """Test single chunk storage operations."""
    
    @pytest.fixture
    def mock_store(self):
        """Create Firestore store with mocked client."""
        with patch('app.storage.firestore_store.firestore.Client') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_doc = MagicMock()
            
            mock_client.return_value = mock_db
            mock_db.collection.return_value = mock_collection
            mock_collection.document.return_value = mock_doc
            
            store = FirestoreChunkStore(project_id="test-project")
            store.mock_doc = mock_doc  # For assertions
            
            yield store
    
    def test_store_chunk_success(self, mock_store):
        """Test successful chunk storage."""
        chunk_data = {
            "text": "Test chunk text",
            "metadata": {"source": "test.pdf", "page": 1},
            "vector": [0.1, 0.2, 0.3]
        }
        
        result = mock_store.store_chunk("chunk_001", chunk_data)
        
        assert result is True
        mock_store.mock_doc.set.assert_called_once()
        
        # Verify data structure
        call_args = mock_store.mock_doc.set.call_args
        stored_data = call_args[0][0]
        
        assert stored_data["chunk_id"] == "chunk_001"
        assert stored_data["text"] == "Test chunk text"
        assert stored_data["metadata"] == {"source": "test.pdf", "page": 1}
        assert stored_data["vector"] == [0.1, 0.2, 0.3]
    
    def test_store_chunk_empty_metadata(self, mock_store):
        """Test storing chunk without metadata."""
        chunk_data = {
            "text": "Test chunk",
            "vector": [0.1, 0.2]
        }
        
        result = mock_store.store_chunk("chunk_002", chunk_data)
        
        assert result is True
        call_args = mock_store.mock_doc.set.call_args
        stored_data = call_args[0][0]
        
        assert stored_data["metadata"] == {}
    
    def test_store_chunk_empty_vector(self, mock_store):
        """Test storing chunk without vector."""
        chunk_data = {
            "text": "Test chunk",
            "metadata": {"source": "test.pdf"}
        }
        
        result = mock_store.store_chunk("chunk_003", chunk_data)
        
        assert result is True
        call_args = mock_store.mock_doc.set.call_args
        stored_data = call_args[0][0]
        
        assert stored_data["vector"] == []
    
    def test_store_chunk_merge_true(self, mock_store):
        """Test that store uses merge=True."""
        chunk_data = {"text": "Test"}
        
        mock_store.store_chunk("chunk_004", chunk_data)
        
        call_args = mock_store.mock_doc.set.call_args
        assert call_args[1]["merge"] is True
    
    def test_store_chunk_firestore_error(self, mock_store):
        """Test handling of Firestore errors."""
        mock_store.mock_doc.set.side_effect = Exception("Firestore write error")
        
        chunk_data = {"text": "Test chunk"}
        result = mock_store.store_chunk("chunk_005", chunk_data)
        
        assert result is False
    
    def test_store_chunk_no_collection(self):
        """Test storing chunk when collection is None."""
        with patch('app.storage.firestore_store.firestore.Client') as mock_client:
            mock_client.side_effect = Exception("Connection failed")
            
            store = FirestoreChunkStore(project_id="test-project")
            result = store.store_chunk("chunk_006", {"text": "Test"})
            
            assert result is False
    
    def test_store_chunk_includes_timestamps(self, mock_store):
        """Test that stored chunks include timestamps."""
        chunk_data = {"text": "Test chunk"}
        
        mock_store.store_chunk("chunk_007", chunk_data)
        
        call_args = mock_store.mock_doc.set.call_args
        stored_data = call_args[0][0]
        
        assert "created_at" in stored_data
        assert "updated_at" in stored_data
        assert stored_data["created_at"] == firestore.SERVER_TIMESTAMP
        assert stored_data["updated_at"] == firestore.SERVER_TIMESTAMP


class TestFirestoreChunkStoreBatchStore:
    """Test batch chunk storage operations."""
    
    @pytest.fixture
    def mock_store(self):
        """Create Firestore store with mocked batch operations."""
        with patch('app.storage.firestore_store.firestore.Client') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_batch = MagicMock()
            
            mock_client.return_value = mock_db
            mock_db.collection.return_value = mock_collection
            mock_db.batch.return_value = mock_batch
            
            store = FirestoreChunkStore(project_id="test-project")
            store.mock_batch = mock_batch
            store.mock_collection = mock_collection
            
            yield store
    
    def test_batch_store_chunks_success(self, mock_store):
        """Test successful batch storage."""
        chunks = {
            "chunk_001": {"text": "Chunk 1", "vector": [0.1]},
            "chunk_002": {"text": "Chunk 2", "vector": [0.2]},
            "chunk_003": {"text": "Chunk 3", "vector": [0.3]}
        }
        
        result = mock_store.batch_store_chunks(chunks)
        
        assert result == 3
        assert mock_store.mock_batch.set.call_count == 3
        mock_store.mock_batch.commit.assert_called_once()
    
    def test_batch_store_empty_chunks(self, mock_store):
        """Test batch storage with empty chunks dict."""
        result = mock_store.batch_store_chunks({})
        
        assert result == 0
        mock_store.mock_batch.set.assert_not_called()
    
    def test_batch_store_single_chunk(self, mock_store):
        """Test batch storage with single chunk."""
        chunks = {"chunk_001": {"text": "Single chunk"}}
        
        result = mock_store.batch_store_chunks(chunks)
        
        assert result == 1
        mock_store.mock_batch.set.assert_called_once()
    
    def test_batch_store_500_chunk_limit(self, mock_store):
        """Test that batch commits at 500 chunk limit."""
        # Create 1000 chunks
        chunks = {
            f"chunk_{i:04d}": {"text": f"Chunk {i}"}
            for i in range(1000)
        }
        
        result = mock_store.batch_store_chunks(chunks)
        
        assert result == 1000
        # Should commit twice: at 500 and at 1000
        assert mock_store.mock_batch.commit.call_count == 2
    
    def test_batch_store_exact_500_chunks(self, mock_store):
        """Test batch storage with exactly 500 chunks."""
        chunks = {
            f"chunk_{i:04d}": {"text": f"Chunk {i}"}
            for i in range(500)
        }
        
        result = mock_store.batch_store_chunks(chunks)
        
        assert result == 500
        # Should commit once at 500
        assert mock_store.mock_batch.commit.call_count == 1
    
    def test_batch_store_501_chunks(self, mock_store):
        """Test batch storage with 501 chunks (just over limit)."""
        chunks = {
            f"chunk_{i:04d}": {"text": f"Chunk {i}"}
            for i in range(501)
        }
        
        result = mock_store.batch_store_chunks(chunks)
        
        assert result == 501
        # Should commit twice: at 500 and at 501
        assert mock_store.mock_batch.commit.call_count == 2
    
    def test_batch_store_no_db(self):
        """Test batch storage when db is None."""
        with patch('app.storage.firestore_store.firestore.Client') as mock_client:
            mock_client.side_effect = Exception("Connection failed")
            
            store = FirestoreChunkStore(project_id="test-project")
            result = store.batch_store_chunks({"chunk_001": {"text": "Test"}})
            
            assert result == 0
    
    def test_batch_store_includes_all_fields(self, mock_store):
        """Test that batch stored chunks include all fields."""
        chunks = {
            "chunk_001": {
                "text": "Test text",
                "metadata": {"key": "value"},
                "vector": [0.1, 0.2, 0.3]
            }
        }
        
        mock_store.batch_store_chunks(chunks)
        
        call_args = mock_store.mock_batch.set.call_args[0]
        stored_data = call_args[1]
        
        assert "chunk_id" in stored_data
        assert "text" in stored_data
        assert "metadata" in stored_data
        assert "vector" in stored_data
        assert "created_at" in stored_data
        assert "updated_at" in stored_data
    
    def test_batch_store_merge_flag(self, mock_store):
        """Test that batch operations use merge=True."""
        chunks = {"chunk_001": {"text": "Test"}}
        
        mock_store.batch_store_chunks(chunks)
        
        call_args = mock_store.mock_batch.set.call_args
        assert call_args[1]["merge"] is True


class TestFirestoreChunkStoreGetChunk:
    """Test chunk retrieval operations."""
    
    @pytest.fixture
    def mock_store(self):
        """Create Firestore store with mocked retrieval."""
        with patch('app.storage.firestore_store.firestore.Client') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_doc_ref = MagicMock()
            
            mock_client.return_value = mock_db
            mock_db.collection.return_value = mock_collection
            mock_collection.document.return_value = mock_doc_ref
            
            store = FirestoreChunkStore(project_id="test-project")
            store.mock_doc_ref = mock_doc_ref
            
            yield store
    
    def test_get_chunk_exists(self, mock_store):
        """Test retrieving existing chunk."""
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = True
        mock_doc_snapshot.to_dict.return_value = {
            "chunk_id": "chunk_001",
            "text": "Test text",
            "metadata": {"source": "test.pdf"},
            "vector": [0.1, 0.2, 0.3]
        }
        
        mock_store.mock_doc_ref.get.return_value = mock_doc_snapshot
        
        result = mock_store.get_chunk("chunk_001")
        
        assert result is not None
        assert result["chunk_id"] == "chunk_001"
        assert result["text"] == "Test text"
    
    def test_get_chunk_not_exists(self, mock_store):
        """Test retrieving non-existent chunk."""
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = False
        
        mock_store.mock_doc_ref.get.return_value = mock_doc_snapshot
        
        result = mock_store.get_chunk("nonexistent")
        
        assert result is None
    
    def test_get_chunk_error(self, mock_store):
        """Test error handling during chunk retrieval."""
        mock_store.mock_doc_ref.get.side_effect = Exception("Firestore read error")
        
        result = mock_store.get_chunk("chunk_001")
        
        assert result is None


class TestFirestoreChunkStoreDeleteChunk:
    """Test chunk deletion operations."""
    
    @pytest.fixture
    def mock_store(self):
        """Create Firestore store with mocked deletion."""
        with patch('app.storage.firestore_store.firestore.Client') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_doc_ref = MagicMock()
            
            mock_client.return_value = mock_db
            mock_db.collection.return_value = mock_collection
            mock_collection.document.return_value = mock_doc_ref
            
            store = FirestoreChunkStore(project_id="test-project")
            store.mock_doc_ref = mock_doc_ref
            
            yield store
    
    def test_delete_chunk_success(self, mock_store):
        """Test successful chunk deletion."""
        result = mock_store.delete_chunk("chunk_001")
        
        assert result is True
        mock_store.mock_doc_ref.delete.assert_called_once()
    
    def test_delete_chunk_error(self, mock_store):
        """Test error handling during deletion."""
        mock_store.mock_doc_ref.delete.side_effect = Exception("Delete failed")
        
        result = mock_store.delete_chunk("chunk_001")
        
        assert result is False
    
    def test_delete_chunk_no_collection(self):
        """Test deletion when collection is None."""
        with patch('app.storage.firestore_store.firestore.Client') as mock_client:
            mock_client.side_effect = Exception("Connection failed")
            
            store = FirestoreChunkStore(project_id="test-project")
            result = store.delete_chunk("chunk_001")
            
            assert result is False


class TestFirestoreChunkStoreQueryChunks:
    """Test chunk querying operations."""
    
    @pytest.fixture
    def mock_store(self):
        """Create Firestore store with mocked queries."""
        with patch('app.storage.firestore_store.firestore.Client') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_query = MagicMock()
            
            mock_client.return_value = mock_db
            mock_db.collection.return_value = mock_collection
            mock_collection.where.return_value = mock_query
            
            store = FirestoreChunkStore(project_id="test-project")
            store.mock_query = mock_query
            
            yield store
    
    def test_query_chunks_by_metadata(self, mock_store):
        """Test querying chunks by metadata field."""
        mock_docs = [
            MagicMock(id="chunk_001", to_dict=lambda: {"text": "Text 1"}),
            MagicMock(id="chunk_002", to_dict=lambda: {"text": "Text 2"})
        ]
        mock_store.mock_query.stream.return_value = mock_docs
        
        results = mock_store.query_chunks_by_metadata("source", "test.pdf")
        
        assert len(results) == 2
        assert results[0]["id"] == "chunk_001"
        assert results[1]["id"] == "chunk_002"
    
    def test_query_chunks_empty_results(self, mock_store):
        """Test query with no matching chunks."""
        mock_store.mock_query.stream.return_value = []
        
        results = mock_store.query_chunks_by_metadata("source", "nonexistent.pdf")
        
        assert len(results) == 0
    
    def test_query_chunks_error(self, mock_store):
        """Test error handling during query."""
        mock_store.mock_query.stream.side_effect = Exception("Query failed")
        
        results = mock_store.query_chunks_by_metadata("source", "test.pdf")
        
        assert len(results) == 0


class TestFirestoreChunkStoreEdgeCases:
    """Test edge cases and error handling."""
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_very_large_chunk(self, mock_client):
        """Test storing very large chunk."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_doc = MagicMock()
        
        mock_client.return_value = mock_db
        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc
        
        store = FirestoreChunkStore(project_id="test-project")
        
        # Create large chunk (1MB of text)
        large_chunk = {
            "text": "A" * 1_000_000,
            "vector": [0.1] * 10000
        }
        
        result = store.store_chunk("large_chunk", large_chunk)
        assert result is True
    
    @patch('app.storage.firestore_store.firestore.Client')
    def test_special_characters_in_chunk_id(self, mock_client):
        """Test chunk ID with special characters."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_doc = MagicMock()
        
        mock_client.return_value = mock_db
        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc
        
        store = FirestoreChunkStore(project_id="test-project")
        
        # Test various special characters
        special_ids = [
            "chunk-with-dash",
            "chunk_with_underscore",
            "chunk.with.dots",
            "chunk@with@at"
        ]
        
        for chunk_id in special_ids:
            result = store.store_chunk(chunk_id, {"text": "Test"})
            assert result is True
