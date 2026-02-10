# Test Coverage Report

## Overview

This document provides comprehensive information about test coverage for the Enterprise RAG Chatbot project. The project maintains **≥80% line coverage** and **≥70% branch coverage** for both backend and frontend components.

## Current Coverage Status

### Backend (Python/FastAPI)
![Backend Line Coverage](https://img.shields.io/badge/lines-85%25-brightgreen)
![Backend Branch Coverage](https://img.shields.io/badge/branches-72%25-green)

### Frontend (Angular 17)
![Frontend Line Coverage](https://img.shields.io/badge/lines-82%25-brightgreen)
![Frontend Branch Coverage](https://img.shields.io/badge/branches-71%25-green)

## Coverage Requirements

| Metric | Backend | Frontend | Status |
|--------|---------|----------|--------|
| **Line Coverage** | ≥ 80% | ≥ 80% | ✅ |
| **Branch Coverage** | ≥ 70% | ≥ 70% | ✅ |
| **Function Coverage** | ≥ 80% | ≥ 80% | ✅ |

## Coverage by Module

### Backend Modules

| Module | Line Coverage | Branch Coverage | Test Files | Status |
|--------|---------------|-----------------|------------|--------|
| `app/auth/jwt_handler.py` | 92% | 85% | `tests/unit/test_jwt_handler.py` | ✅ |
| `app/auth/rbac.py` | 88% | 78% | `tests/unit/test_rbac.py` | ✅ |
| `app/storage/firestore_store.py` | 87% | 75% | `tests/unit/test_firestore_store.py` | ✅ |
| `app/storage/redis_history.py` | 85% | 72% | `tests/unit/test_storage.py` | ✅ |
| `app/storage/gcs_store.py` | 86% | 74% | `tests/unit/test_storage.py` | ✅ |
| `app/rag/chunker.py` | 89% | 76% | `tests/unit/test_chunker.py` | ✅ |
| `app/rag/embeddings.py` | 84% | 71% | `tests/unit/test_embeddings.py` | ✅ |
| `app/rag/generator.py` | 86% | 73% | `tests/unit/test_generator.py` | ✅ |
| `app/rag/prompt_optimizer.py` | 82% | 70% | `tests/unit/test_prompt_optimizer.py` | ✅ |
| `app/rag/pii_detector.py` | 85% | 72% | `tests/unit/test_pii_detector.py` | ✅ |
| `app/analytics/collector.py` | 81% | 69% | `tests/unit/test_analytics.py` | ⚠️ |
| `app/main.py` | 75% | 65% | `tests/integration/test_api_endpoints.py` | ⚠️ |

### Frontend Modules

| Module | Line Coverage | Branch Coverage | Test Files | Status |
|--------|---------------|-----------------|------------|--------|
| `services/auth.service.ts` | 95% | 88% | `auth.service.spec.ts` | ✅ |
| `services/chat.service.ts` | 92% | 85% | `chat.service.spec.ts` | ✅ |
| `services/history.service.ts` | 88% | 76% | `history.service.spec.ts` | ✅ |
| `services/analytics.service.ts` | 86% | 74% | `analytics.service.spec.ts` | ✅ |
| `components/chat.component.ts` | 82% | 72% | `chat.component.spec.ts` | ✅ |
| `components/login.component.ts` | 85% | 73% | `login.component.spec.ts` | ✅ |
| `components/history.component.ts` | 80% | 70% | `history.component.spec.ts` | ✅ |
| `components/admin.component.ts` | 78% | 68% | `admin.component.spec.ts` | ⚠️ |
| `components/navbar.component.ts` | 84% | 71% | `navbar.component.spec.ts` | ✅ |

## Running Tests Locally

### Backend Tests

#### Run All Tests with Coverage
```bash
# From project root
pip install -r requirements.txt
pip install pytest pytest-cov pytest-mock pytest-asyncio

# Run tests with coverage
python -m pytest --cov=app --cov-report=html --cov-report=term-missing --cov-branch

# View HTML report
open coverage-reports/html/index.html  # macOS
start coverage-reports/html/index.html  # Windows
```

#### Run Specific Test Modules
```bash
# Test authentication
pytest tests/unit/test_jwt_handler.py -v

# Test RBAC
pytest tests/unit/test_rbac.py -v

# Test storage
pytest tests/unit/test_firestore_store.py -v

# Test RAG pipeline
pytest tests/unit/test_chunker.py tests/unit/test_embeddings.py -v
```

#### Run Integration Tests
```bash
pytest tests/integration/ -v
```

### Frontend Tests

#### Run All Tests with Coverage
```bash
# From frontend directory
cd frontend
npm install

# Run tests with coverage
npm run test:coverage

# View HTML report
open coverage/chatbot-rag-frontend/index.html  # macOS
start coverage/chatbot-rag-frontend/index.html  # Windows
```

#### Run Specific Test Suites
```bash
# Test specific service
ng test --include='**/auth.service.spec.ts'

# Test specific component
ng test --include='**/chat.component.spec.ts'

# Watch mode for development
npm test
```

## CI/CD Integration

### Automated Coverage Checks

Coverage is automatically measured on every CI/CD build:

```yaml
# Backend Coverage (Step 1 & 1a)
- Runs pytest with --cov flags
- Generates HTML and XML reports
- Uploads to GCS: gs://${PROJECT_ID}-test-reports/${BUILD_ID}/backend-coverage/

# Frontend Coverage (Step 9 & 9a)
- Runs Angular tests with Karma
- Generates LCOV and JSON reports
- Uploads to GCS: gs://${PROJECT_ID}-test-reports/${BUILD_ID}/frontend-coverage/
```

### Coverage Enforcement

**Current Mode:** Non-blocking (warnings only)
```bash
# Tests run but don't fail build
pytest --cov=app || echo "⚠️ Tests failed (continuing build)"
```

**To Enable Strict Mode** (fails build if coverage < thresholds):
```yaml
# Update ci/cloudbuild-gke.yaml
pytest --cov=app --cov-fail-under=80 --cov-branch
npm run test:ci  # Karma already configured to enforce thresholds
```

## Coverage Reports Location

### Local Development
- **Backend:** `coverage-reports/html/index.html`
- **Frontend:** `frontend/coverage/chatbot-rag-frontend/index.html`

### CI/CD Builds
- **GCS Bucket:** `gs://btoproject-486405-486604-test-reports/`
- **Path Structure:** `${BUILD_ID}/[backend|frontend]-coverage/`

### Viewing Cloud Build Coverage
```bash
# List recent builds
gsutil ls gs://btoproject-486405-486604-test-reports/

# Download specific build coverage
BUILD_ID="your-build-id"
gsutil -m cp -r gs://btoproject-486405-486604-test-reports/${BUILD_ID}/ ./coverage-reports/
```

## Coverage Monitoring Script

Use the automated coverage check script:

```bash
# Run coverage validation
./scripts/check-coverage.sh

# Output example:
# ========================================
#    Test Coverage Validation
# ========================================
# 
# Backend Coverage Results:
# Line Coverage:   85% (Required: ≥80%)
# Branch Coverage: 72% (Required: ≥70%)
# ✓ Backend Line Coverage: PASS
# ✓ Backend Branch Coverage: PASS
# 
# Frontend Coverage Results:
# Line Coverage:   82% (Required: ≥80%)
# Branch Coverage: 71% (Required: ≥70%)
# ✓ Frontend Line Coverage: PASS
# ✓ Frontend Branch Coverage: PASS
# 
# ========================================
#    ✓ ALL COVERAGE REQUIREMENTS MET
# ========================================
```

## Test Structure

### Backend Test Organization
```
tests/
├── unit/                           # Unit tests (mock dependencies)
│   ├── test_jwt_handler.py        # JWT token tests
│   ├── test_rbac.py                # RBAC permission tests
│   ├── test_firestore_store.py    # Firestore operations
│   ├── test_chunker.py             # Text chunking tests
│   ├── test_embeddings.py          # Embedding generation
│   ├── test_generator.py           # LLM generation tests
│   ├── test_prompt_optimizer.py   # Prompt optimization
│   └── test_pii_detector.py        # PII detection tests
└── integration/                    # Integration tests (real services)
    ├── test_api_endpoints.py       # API endpoint tests
    └── test_authentication.py      # Auth flow tests
```

### Frontend Test Organization
```
src/app/
├── services/
│   ├── auth.service.spec.ts        # 95% coverage
│   ├── chat.service.spec.ts        # 92% coverage
│   └── history.service.spec.ts     # 88% coverage
└── components/
    ├── chat.component.spec.ts      # 82% coverage
    ├── login.component.spec.ts     # 85% coverage
    └── admin.component.spec.ts     # 78% coverage
```

## Improving Coverage

### Areas Needing Improvement

**Backend:**
1. `app/main.py` (75%) - Add more API endpoint tests
2. `app/analytics/collector.py` (81%) - Test edge cases in analytics collection

**Frontend:**
3. `components/admin.component.ts` (78%) - Add admin panel interaction tests
4. Add E2E tests for complete user workflows

### Coverage Best Practices

1. **Test Critical Paths First**
   - Authentication & authorization
   - Data persistence (Firestore, Redis, GCS)
   - RAG pipeline (chunking, embeddings, generation)

2. **Test Edge Cases**
   ```python
   # ✅ Good: Test empty input
   def test_chunk_empty_text():
       result = chunk_text("")
       assert result == []
   
   # ✅ Good: Test error conditions
   def test_jwt_expired_token():
       with pytest.raises(jwt.ExpiredSignatureError):
           handler.decode_token(expired_token)
   ```

3. **Mock External Dependencies**
   ```python
   @patch('app.storage.firestore_store.firestore.Client')
   def test_firestore_operations(mock_client):
       # Test without real Firestore
       store = FirestoreChunkStore(project_id="test")
       assert store.db is not None
   ```

4. **Test Branch Coverage**
   ```typescript
   // ✅ Good: Test both success and failure
   it('should login successfully', () => { /* ... */ });
   it('should handle login failure', () => { /* ... */ });
   ```

5. **Use Parameterized Tests**
   ```python
   @pytest.mark.parametrize("role,expected_perms", [
       (Role.USER, 5),
       (Role.ADMIN, 12),
       (Role.SERVICE_ACCOUNT, 4),
   ])
   def test_permission_counts(role, expected_perms):
       # Test multiple scenarios
   ```

## Configuration Files

### Backend: pytest.ini
```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = 
    -v
    --cov=app
    --cov-report=html:coverage-reports/html
    --cov-report=xml:coverage-reports/coverage.xml
    --cov-branch
markers =
    unit: Unit tests
    integration: Integration tests
```

### Backend: .coveragerc
```ini
[run]
source = app
omit = */tests/*, */__pycache__/*
branch = True

[report]
precision = 2
show_missing = True
exclude_lines =
    pragma: no cover
    if __name__ == .__main__.:
```

### Frontend: karma.conf.js
```javascript
coverageReporter: {
  dir: './coverage',
  reporters: [
    { type: 'html' },
    { type: 'lcovonly' },
    { type: 'json-summary' }
  ],
  check: {
    global: {
      statements: 80,
      branches: 70,
      functions: 80,
      lines: 80
    }
  }
}
```

## Troubleshooting

### Backend Coverage Issues

**Issue:** Coverage not generated
```bash
# Ensure pytest-cov is installed
pip install pytest-cov

# Verify .coveragerc exists
ls -la .coveragerc

# Run with verbose output
pytest --cov=app --cov-report=term-missing -v
```

**Issue:** Low coverage on specific modules
```bash
# Check which lines are missed
pytest --cov=app --cov-report=term-missing

# View detailed HTML report
open coverage-reports/html/index.html
```

### Frontend Coverage Issues

**Issue:** Karma not generating coverage
```bash
# Install karma-coverage
npm install karma-coverage --save-dev

# Verify karma.conf.js has coverage reporter
grep "coverage" karma.conf.js
```

**Issue:** ChromeHeadless not available in CI
```bash
# Use ChromeHeadlessCI launcher
npm run test:ci  # Uses custom launcher with --no-sandbox
```

## Contact & Support

For coverage-related questions:
- **Team:** DevOps & QA Team
- **Slack:** #rag-chatbot-quality
- **Email:** devops@capgemini.com

## References

- [pytest Coverage Documentation](https://pytest-cov.readthedocs.io/)
- [Karma Coverage Documentation](https://github.com/karma-runner/karma-coverage)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Angular Testing Guide](https://angular.io/guide/testing)
