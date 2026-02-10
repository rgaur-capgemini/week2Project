# Pytest Configuration
import sys
import os
import logging
from pathlib import Path
from unittest.mock import MagicMock, Mock

# Create mock classes that behave more like real objects
class MockCloudLoggingHandler:
    """Mock CloudLoggingHandler that works with Python logging."""
    def __init__(self, *args, **kwargs):
        self.level = logging.INFO
    def emit(self, record):
        pass

class MockCloudLogging:
    """Mock Cloud Logging module."""
    def Client(self, *args, **kwargs):
        return MagicMock()
    def __getattr__(self, name):
        return MagicMock()

# Mock ALL Google Cloud modules before any imports
# This prevents ImportError when modules try to import google.cloud packages
sys.modules['google'] = MagicMock()
sys.modules['google.cloud'] = MagicMock()
sys.modules['google.cloud.logging'] = MockCloudLogging()
sys.modules['google.cloud.logging.handlers'] = Mock(CloudLoggingHandler=MockCloudLoggingHandler)
sys.modules['google.cloud.aiplatform'] = MagicMock()
sys.modules['google.cloud.storage'] = MagicMock()
sys.modules['google.cloud.firestore'] = MagicMock()
sys.modules['google.cloud.secretmanager_v1'] = MagicMock()
sys.modules['google.cloud.dlp_v2'] = MagicMock()
sys.modules['google.auth'] = MagicMock()
sys.modules['google.auth.transport'] = MagicMock()
sys.modules['google.auth.transport.requests'] = MagicMock()
sys.modules['google.oauth2'] = MagicMock()
sys.modules['google.oauth2.id_token'] = MagicMock()

# Mock vertexai modules before any imports
sys.modules['vertexai'] = MagicMock()
sys.modules['vertexai.language_models'] = MagicMock()
sys.modules['vertexai.generative_models'] = MagicMock()
sys.modules['vertexai.matching_engine'] = MagicMock()
sys.modules['vertexai.preview'] = MagicMock()
sys.modules['vertexai.preview.language_models'] = MagicMock()

# Mock Redis
sys.modules['redis'] = MagicMock()
sys.modules['redis.exceptions'] = MagicMock()

# Mock LangChain and LangGraph
sys.modules['langchain'] = MagicMock()
sys.modules['langchain_core'] = MagicMock()
sys.modules['langchain_core.messages'] = MagicMock()
sys.modules['langchain_google_vertexai'] = MagicMock()
sys.modules['langgraph'] = MagicMock()
sys.modules['langgraph.graph'] = MagicMock()

# Mock OpenTelemetry
sys.modules['opentelemetry'] = MagicMock()
sys.modules['opentelemetry.trace'] = MagicMock()
sys.modules['opentelemetry.metrics'] = MagicMock()
sys.modules['opentelemetry.sdk'] = MagicMock()
sys.modules['opentelemetry.sdk.trace'] = MagicMock()
sys.modules['opentelemetry.sdk.trace.export'] = MagicMock()
sys.modules['opentelemetry.sdk.metrics'] = MagicMock()
sys.modules['opentelemetry.sdk.metrics.export'] = MagicMock()
sys.modules['opentelemetry.sdk.resources'] = MagicMock()
sys.modules['opentelemetry.exporter'] = MagicMock()
sys.modules['opentelemetry.exporter.cloud_trace'] = MagicMock()
sys.modules['opentelemetry.exporter.cloud_monitoring'] = MagicMock()
sys.modules['opentelemetry.instrumentation'] = MagicMock()
sys.modules['opentelemetry.instrumentation.fastapi'] = MagicMock()

# Mock BeautifulSoup
sys.modules['bs4'] = MagicMock()

# Mock PyPDF2
sys.modules['PyPDF2'] = MagicMock()

# Mock python-docx
sys.modules['docx'] = MagicMock()

# Mock NumPy (needed by vector operations)
import types
numpy_module = types.ModuleType('numpy')
numpy_module.array = lambda x, **kwargs: x
numpy_module.ndarray = list
numpy_module.float32 = float
numpy_module.float64 = float
numpy_module.int32 = int
numpy_module.int64 = int
numpy_module.zeros = lambda *args, **kwargs: [0] * (args[0] if args else 1)
numpy_module.ones = lambda *args, **kwargs: [1] * (args[0] if args else 1)
numpy_module.dot = lambda x, y: sum(a*b for a,b in zip(x, y))
numpy_module.linalg = MagicMock()
numpy_module.linalg.norm = lambda x: sum(a**2 for a in x) ** 0.5
sys.modules['numpy'] = numpy_module

# Mock JWT
sys.modules['jwt'] = MagicMock()

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
