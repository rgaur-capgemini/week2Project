# Pytest Configuration
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import pytest
from typing import Generator
from unittest.mock import MagicMock, patch

# Configure pytest
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "gcp: Tests requiring GCP services")


@pytest.fixture(scope="session")
def mock_gcp_credentials():
    """Mock GCP credentials for all tests."""
    with patch.dict(os.environ, {
        "GOOGLE_APPLICATION_CREDENTIALS": "/fake/path/credentials.json",
        "PROJECT_ID": "test-project",
        "REGION": "us-central1"
    }):
        yield


@pytest.fixture
def mock_secret_manager():
    """Mock Secret Manager client."""
    with patch("google.cloud.secretmanager_v1.SecretManagerServiceClient") as mock:
        mock_client = MagicMock()
        mock_client.access_secret_version.return_value.payload.data = b"test-secret"
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_vertex_ai():
    """Mock Vertex AI services."""
    with patch("google.cloud.aiplatform.TextEmbeddingModel") as mock_embed, \
         patch("google.cloud.aiplatform.GenerativeModel") as mock_gen:
        
        # Mock embeddings
        mock_embed_instance = MagicMock()
        mock_embed_instance.get_embeddings.return_value = [
            MagicMock(values=[0.1] * 768)
        ]
        mock_embed.from_pretrained.return_value = mock_embed_instance
        
        # Mock generation
        mock_gen_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Test answer"
        mock_gen_instance.generate_content.return_value = mock_response
        mock_gen.return_value = mock_gen_instance
        
        yield {"embeddings": mock_embed_instance, "generation": mock_gen_instance}


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("redis.Redis") as mock:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = None
        mock_client.set.return_value = True
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_firestore():
    """Mock Firestore client."""
    with patch("google.cloud.firestore.Client") as mock:
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.collection.return_value = mock_collection
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_gcs():
    """Mock Google Cloud Storage."""
    with patch("google.cloud.storage.Client") as mock:
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.public_url = "https://storage.googleapis.com/test-bucket/test-file"
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return """
    This is a sample document for testing.
    
    It has multiple paragraphs with different content.
    Each paragraph should be processed correctly.
    
    The document contains important information about testing.
    We need to ensure all components work as expected.
    """


@pytest.fixture
def sample_chunks():
    """Sample chunks for testing."""
    return [
        {
            "id": "doc1-0",
            "text": "First chunk of text with important information.",
            "metadata": {"source": "doc1.txt", "chunk": 0}
        },
        {
            "id": "doc1-1",
            "text": "Second chunk with more details about the topic.",
            "metadata": {"source": "doc1.txt", "chunk": 1}
        },
        {
            "id": "doc2-0",
            "text": "Third chunk from a different document.",
            "metadata": {"source": "doc2.txt", "chunk": 0}
        }
    ]


@pytest.fixture
def sample_question():
    """Sample question for testing."""
    return "What is the main topic of the document?"


@pytest.fixture
def sample_contexts():
    """Sample contexts for testing."""
    return [
        "The document discusses machine learning algorithms.",
        "Deep learning is a subset of machine learning.",
        "Neural networks are used in deep learning applications."
    ]
