# Test Debugging Guide - GCP Cloud Build

## Overview
This guide helps diagnose and fix test failures in GCP Cloud Build environment.

## Quick Diagnosis Commands

### 1. View Full Test Output in Cloud Build
```bash
# View recent build logs
gcloud builds list --limit=5

# Get detailed logs for specific build
gcloud builds log <BUILD_ID>

# Stream live build logs
gcloud builds log <BUILD_ID> --stream

# Download full log file
gcloud builds log <BUILD_ID> > build-log.txt
```

### 2. Run Tests Locally with Same Configuration
```bash
# Activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run tests with verbose output
pytest -v --tb=long --maxfail=5

# Run specific failing test with full traceback
pytest tests/unit/test_main.py::TestHealthEndpoints::test_liveness_endpoint -vvs --tb=long

# Run with pdb debugger on first failure
pytest --pdb -x
```

### 3. Check Test Collection Issues
```bash
# List all tests without running them
pytest --collect-only

# Check for import errors
pytest --collect-only -v

# Verify specific test file can be collected
pytest --collect-only tests/unit/test_main.py
```

## Common Failure Patterns

### Pattern 1: Import Errors
**Symptom:** `ImportError: cannot import name 'X' from 'module'`

**Diagnosis:**
```bash
# Check if module exists
python -c "from app.rag.embeddings import VertexTextEmbedder"

# List what's available in module
python -c "import app.rag.embeddings; print(dir(app.rag.embeddings))"

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"
```

**Common Causes:**
- Class name mismatch in test vs actual code
- Missing `__init__.py` files
- Circular imports
- Module not installed in environment

**Fix:**
```bash
# Verify class names match
grep -r "class VertexTextEmbedder" app/

# Check imports in test file
head -n 20 tests/unit/test_embeddings.py
```

### Pattern 2: Attribute Errors
**Symptom:** `AttributeError: module 'X' has no attribute 'Y'`

**Diagnosis:**
```bash
# Run failing test with verbose output
pytest tests/unit/test_embeddings.py::TestVertexTextEmbedder::test_embed_single_text -vvs

# Check what the module actually exports
python -c "import app.rag.embeddings; print(vars(app.rag.embeddings))"
```

**Common Causes:**
- Mock object missing expected attributes
- Wrong object being mocked
- Typo in attribute name

**Fix:**
- Update mock to include missing attributes
- Verify mock.return_value vs mock side effects
- Check actual class interface

### Pattern 3: Configuration/Environment Issues
**Symptom:** Tests work locally but fail in Cloud Build

**Diagnosis:**
```bash
# Check environment variables in Cloud Build
echo $PROJECT_ID
echo $PYTHONPATH
echo $GOOGLE_CLOUD_PROJECT

# Compare Python versions
python --version

# Check installed packages
pip list | grep -E "(pytest|mock|asyncio)"
```

**Common Causes:**
- Missing environment variables
- Different Python versions
- Missing GCP credentials
- Wrong working directory

**Fix:**
- Set environment variables in cloudbuild.yaml
- Use substitutions for dynamic values
- Mock all GCP service calls

### Pattern 4: Async Test Failures
**Symptom:** `RuntimeError: Event loop is closed` or `RuntimeError: no running event loop`

**Diagnosis:**
```bash
# Check if pytest-asyncio is installed
pip show pytest-asyncio

# Verify test has @pytest.mark.asyncio decorator
grep -A 5 "async def test_" tests/unit/test_main.py
```

**Common Causes:**
- Missing `@pytest.mark.asyncio` decorator
- Event loop not properly closed
- Multiple event loops interfering

**Fix:**
```python
# Add decorator to async tests
@pytest.mark.asyncio
async def test_my_async_function():
    result = await my_async_function()
    assert result is not None
```

### Pattern 5: Mock/Fixture Issues
**Symptom:** `TypeError: 'MagicMock' object is not callable` or `AttributeError: mock object has no attribute`

**Diagnosis:**
```bash
# Run test with debug output
pytest tests/unit/test_main.py -vvs --capture=no

# Check mock setup
grep -A 10 "@patch" tests/unit/test_main.py
```

**Common Causes:**
- Mock not configured correctly
- Missing return_value or side_effect
- Wrong patch target

**Fix:**
```python
# Correct mock setup
with patch('app.main.embedder') as mock_embedder:
    mock_embedder.embed_texts.return_value = [[0.1] * 768]
    # Your test code
```

## Test File Specific Debugging

### test_main.py Failures

**Check FastAPI TestClient setup:**
```python
# Verify imports
from fastapi.testclient import TestClient
from app.main import app

# Check client initialization
client = TestClient(app)
```

**Check mocked services:**
```bash
# List all services that need mocking
grep -E "(embedder|generator|vector_store|pii_detector)" app/main.py

# Verify all are mocked in test
grep -E "@patch|Mock" tests/unit/test_main.py
```

**Run individual test class:**
```bash
pytest tests/unit/test_main.py::TestHealthEndpoints -v
pytest tests/unit/test_main.py::TestIngestEndpoint -v
pytest tests/unit/test_main.py::TestQueryEndpoint -v
```

### test_embeddings.py Failures

**Verify class name:**
```bash
# Check actual class name in source
grep "^class.*Embed" app/rag/embeddings.py

# Check import in test
grep "from app.rag.embeddings import" tests/unit/test_embeddings.py
```

**Check mock setup:**
```python
# Verify VertexTextEmbedder is properly mocked
with patch('vertexai.language_models.TextEmbeddingModel.from_pretrained') as mock_model:
    mock_instance = MagicMock()
    mock_instance.get_embeddings.return_value = [MagicMock(values=[0.1] * 768)]
    mock_model.return_value = mock_instance
```

### test_config.py Failures

**Check environment variables:**
```bash
# Set required env vars
export PROJECT_ID="btoproject-486405-486604"
export REGION="us-central1"
export ENVIRONMENT="test"

# Run test
pytest tests/unit/test_config.py -v
```

**Mock Secret Manager:**
```python
with patch('google.cloud.secretmanager.SecretManagerServiceClient'):
    # Your test code
```

### test_jwt_handler.py Failures

**Check JWT secret:**
```python
# Mock secret retrieval
with patch('app.auth.jwt_handler.get_secret') as mock_secret:
    mock_secret.return_value = "test-secret-key-32-characters-long"
    # Your test code
```

### Integration Test Failures

**Common issue: Missing GCP credentials**
```bash
# Check if credentials are available
echo $GOOGLE_APPLICATION_CREDENTIALS
gcloud auth application-default print-access-token

# Set test credentials
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

**Mock external services:**
- All Vertex AI calls
- All Firestore operations
- All GCS operations
- All Redis operations

## Cloud Build Specific Debugging

### View Test Results in Cloud Build

**Step 1: Check Build Status**
```bash
gcloud builds list --project=btoproject-486405-486604 --limit=10
```

**Step 2: Get Full Build Log**
```bash
BUILD_ID="<your-build-id>"
gcloud builds log $BUILD_ID --project=btoproject-486405-486604 > full-build.log
```

**Step 3: Extract Test Failures**
```bash
# Extract only failed tests
grep "FAILED" full-build.log | sort | uniq

# Extract error messages
grep -A 5 "ERROR" full-build.log

# Extract assertion errors
grep -A 10 "AssertionError" full-build.log

# Count failures by type
grep "FAILED" full-build.log | cut -d':' -f1-2 | sort | uniq -c | sort -rn
```

### Update Cloud Build for Better Debugging

**Add these to cloudbuild-gke.yaml:**
```yaml
# Backend test step with detailed output
- name: 'python:3.11'
  id: 'backend-test-verbose'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      pip install -r requirements.txt
      
      # Run tests with maximum verbosity
      pytest tests/ -v --tb=long --maxfail=10 \
        --cov=app \
        --cov-report=term-missing \
        --cov-report=html:coverage-reports/html \
        --cov-report=xml:coverage-reports/coverage.xml \
        --junitxml=test-results/junit.xml \
        2>&1 | tee test-output.log
      
      # Save exit code
      TEST_EXIT_CODE=${PIPESTATUS[0]}
      
      # Always show coverage summary
      coverage report --precision=2
      
      # Show first 50 failures
      grep "FAILED" test-output.log | head -50
      
      # Exit with test exit code
      exit $TEST_EXIT_CODE
  waitFor: ['-']
```

### Run Specific Test Subset in Cloud Build

Create `test-subset.yaml`:
```yaml
steps:
  - name: 'python:3.11'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        pip install -r requirements.txt
        
        # Test only main.py tests
        pytest tests/unit/test_main.py -v --tb=long
        
        # Test only embeddings
        pytest tests/unit/test_embeddings.py -v --tb=long
        
        # Test only config
        pytest tests/unit/test_config.py -v --tb=long
```

Run:
```bash
gcloud builds submit --config=test-subset.yaml
```

## Systematic Debugging Workflow

### Step 1: Identify Failure Category
```bash
# Count failures by test file
grep "FAILED tests/" build-log.txt | cut -d'/' -f2 | cut -d':' -f1 | sort | uniq -c

# Example output:
#   45 unit
#   32 integration
```

### Step 2: Run Single Test File Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Run single file with verbose output
pytest tests/unit/test_main.py -vvs --tb=long 2>&1 | tee test-main-output.log

# Review output
less test-main-output.log
```

### Step 3: Run Single Test Method
```bash
# Most granular level
pytest tests/unit/test_main.py::TestHealthEndpoints::test_liveness_endpoint -vvs --tb=long

# This shows:
# - Full import chain
# - Setup/teardown
# - Actual assertion failure
# - Full stack trace
```

### Step 4: Fix and Verify
```bash
# Make fix in code
# ...

# Re-run just that test
pytest tests/unit/test_main.py::TestHealthEndpoints::test_liveness_endpoint -v

# If passes, run full file
pytest tests/unit/test_main.py -v

# If passes, run all tests
pytest tests/ -v
```

### Step 5: Test in Cloud Build Environment
```bash
# Submit to Cloud Build
git add .
git commit -m "fix: resolve test failures in test_main.py"
git push origin develop

# Monitor build
gcloud builds list --ongoing
gcloud builds log <BUILD_ID> --stream
```

## Common Fixes Reference

### Fix 1: Update Import Statement
```python
# Before (WRONG)
from app.rag.embeddings import EmbeddingGenerator

# After (CORRECT)
from app.rag.embeddings import VertexTextEmbedder
```

### Fix 2: Add Missing Mock Attributes
```python
# Before (INCOMPLETE)
mock_embedder = MagicMock()

# After (COMPLETE)
mock_embedder = MagicMock()
mock_embedder.embed_texts.return_value = [[0.1] * 768]
mock_embedder.embed_query.return_value = [0.1] * 768
```

### Fix 3: Fix Async Test
```python
# Before (WRONG)
def test_async_function():
    result = await my_async_function()

# After (CORRECT)
@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result is not None
```

### Fix 4: Mock Environment Variables
```python
# Add to test setup
@patch.dict(os.environ, {
    'PROJECT_ID': 'test-project',
    'REGION': 'us-central1',
    'ENVIRONMENT': 'test'
})
def test_config_loading():
    config = load_config()
    assert config.project_id == 'test-project'
```

### Fix 5: Mock GCP Services
```python
@patch('google.cloud.firestore.Client')
@patch('google.cloud.storage.Client')
@patch('vertexai.init')
def test_with_gcp_services(mock_vertex, mock_gcs, mock_firestore):
    # Setup mocks
    mock_firestore.return_value = MagicMock()
    mock_gcs.return_value = MagicMock()
    
    # Your test code
    result = function_using_gcp()
    assert result is not None
```

## Emergency Bypass for CI/CD

If tests are blocking deployment and need emergency bypass:

### Option 1: Make Tests Non-Blocking (Temporary)
```yaml
# In cloudbuild-gke.yaml
- name: 'python:3.11'
  id: 'backend-test'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      pytest tests/ -v || echo "⚠️ Tests failed but continuing build"
```

### Option 2: Skip Tests (Emergency Only)
```bash
# Add to commit message
git commit -m "fix: critical production bug [skip-tests]"

# Update cloudbuild trigger to skip on this tag
```

### Option 3: Run Minimal Test Subset
```yaml
# Only run critical integration tests
- name: 'python:3.11'
  id: 'smoke-test'
  args:
    - '-c'
    - 'pytest tests/integration/test_api_endpoints.py::TestHealthEndpoints -v'
```

## Getting Help

### Check Logs
1. **Cloud Build Console:** https://console.cloud.google.com/cloud-build/builds
2. **Cloud Logging:** https://console.cloud.google.com/logs
3. **Error Reporting:** https://console.cloud.google.com/errors

### Common Commands Summary
```bash
# Quick diagnosis
pytest --collect-only                    # Check test collection
pytest -v --maxfail=5                   # Stop after 5 failures
pytest -k "test_main"                   # Run tests matching pattern
pytest tests/unit/test_main.py -v      # Run single file
pytest --lf                             # Re-run last failed tests
pytest --ff                             # Run failures first

# Detailed debugging
pytest -vvs --tb=long                   # Maximum verbosity
pytest --pdb                            # Drop into debugger on failure
pytest --trace                          # Drop into debugger at start
pytest --setup-show                     # Show fixture setup/teardown

# Coverage
pytest --cov=app --cov-report=html     # Generate HTML coverage report
pytest --cov=app --cov-report=term-missing  # Show missing lines
coverage report                         # View coverage summary
coverage html && open htmlcov/index.html  # View HTML report
```

### Test File Templates

**Minimal working test:**
```python
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

class TestExample:
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
```

## Next Steps

1. ✅ Review this guide
2. ✅ Run `pytest --collect-only` to check test collection
3. ✅ Run `pytest -v --maxfail=5` to see first 5 failures
4. ✅ Pick one failing test and debug with `pytest <path> -vvs --tb=long`
5. ✅ Fix the issue
6. ✅ Verify fix locally
7. ✅ Push to Cloud Build
8. ✅ Monitor build logs
9. ✅ Repeat for remaining failures

---

**Remember:** 
- Debug locally first before testing in Cloud Build
- Fix one test file at a time
- Always check imports and class names
- Mock all external services (GCP, Redis, etc.)
- Use verbose output (`-vvs --tb=long`) for debugging

---

*Last Updated: February 10, 2026*
