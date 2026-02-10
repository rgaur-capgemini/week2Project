# Test Failure Quick Reference

## Get Build Logs from GCP

```bash
# List recent builds
gcloud builds list --project=btoproject-486405-486604 --limit=10

# Download full log
BUILD_ID="<your-build-id>"
gcloud builds log $BUILD_ID --project=btoproject-486405-486604 > build-log.txt

# Analyze failures
python scripts/analyze_test_failures.py build-log.txt
```

## Quick Diagnosis Commands

```bash
# View failures only
grep "FAILED" build-log.txt | cut -d':' -f1-3 | sort | uniq -c

# View errors only
grep "ERROR" build-log.txt | head -20

# Count by error type
grep -o "ImportError\|AttributeError\|TypeError\|AssertionError" build-log.txt | sort | uniq -c

# Find most problematic test file
grep "FAILED tests/" build-log.txt | cut -d'/' -f2,3 | cut -d':' -f1 | sort | uniq -c | sort -rn | head -5
```

## Run Tests Locally

```bash
# Single test file
pytest tests/unit/test_main.py -vvs --tb=long

# Single test method
pytest tests/unit/test_main.py::TestHealthEndpoints::test_liveness_endpoint -vvs

# All tests with early exit
pytest tests/ -v --maxfail=10

# Re-run only failures
pytest --lf -v
```

## Common Fixes

### Import Error
```python
# WRONG
from app.rag.embeddings import EmbeddingGenerator

# CORRECT
from app.rag.embeddings import VertexTextEmbedder
```

### Mock Attribute Error
```python
# WRONG
mock_embedder = MagicMock()

# CORRECT
mock_embedder = MagicMock()
mock_embedder.embed_texts.return_value = [[0.1] * 768]
mock_embedder.embed_query.return_value = [0.1] * 768
```

### Async Test Error
```python
# WRONG
def test_async_function():
    result = await my_function()

# CORRECT
@pytest.mark.asyncio
async def test_async_function():
    result = await my_function()
```

## View Test Artifacts in GCS

```bash
BUILD_ID="<your-build-id>"

# View coverage report
gsutil ls gs://btoproject-486405-486604-test-reports/$BUILD_ID/

# Download coverage HTML
gsutil -m cp -r gs://btoproject-486405-486604-test-reports/$BUILD_ID/backend-coverage/ ./coverage-reports/

# View test log
gsutil cat gs://btoproject-486405-486604-test-reports/$BUILD_ID/test-output.log

# Download JUnit XML
gsutil cp gs://btoproject-486405-486604-test-reports/$BUILD_ID/junit.xml ./
```

## Full Documentation

See [docs/TEST_DEBUGGING_GUIDE.md](../docs/TEST_DEBUGGING_GUIDE.md) for comprehensive debugging guide.
