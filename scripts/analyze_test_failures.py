#!/usr/bin/env python3
"""
Quick Test Failure Analyzer for GCP Cloud Build
Analyzes test output and provides actionable debugging insights
"""

import sys
import re
from collections import defaultdict, Counter
from pathlib import Path

def analyze_test_output(log_file):
    """Analyze pytest test output and provide insights"""
    
    if not Path(log_file).exists():
        print(f"❌ Log file not found: {log_file}")
        print(f"💡 Run: gcloud builds log <BUILD_ID> > {log_file}")
        return
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    print("="*70)
    print("🔍 TEST FAILURE ANALYSIS REPORT")
    print("="*70)
    print()
    
    # 1. Extract overall statistics
    passed = len(re.findall(r'PASSED', content))
    failed = len(re.findall(r'FAILED', content))
    errors = len(re.findall(r'ERROR', content))
    
    print("📊 TEST SUMMARY")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   ⚠️  Errors: {errors}")
    print(f"   📈 Total: {passed + failed + errors}")
    
    if failed + errors > 0:
        success_rate = (passed / (passed + failed + errors)) * 100
        print(f"   Success Rate: {success_rate:.1f}%")
    print()
    
    # 2. Analyze failures by test file
    failures_by_file = defaultdict(list)
    error_patterns = Counter()
    
    failed_tests = re.findall(r'FAILED (tests/[^:]+)::(.*?) - (.*?)(?:\n|$)', content)
    for file_path, test_name, error in failed_tests:
        failures_by_file[file_path].append((test_name, error))
        # Extract error type
        if 'ImportError' in error:
            error_patterns['ImportError'] += 1
        elif 'AttributeError' in error:
            error_patterns['AttributeError'] += 1
        elif 'TypeError' in error:
            error_patterns['TypeError'] += 1
        elif 'AssertionError' in error:
            error_patterns['AssertionError'] += 1
        elif 'NameError' in error:
            error_patterns['NameError'] += 1
        else:
            error_patterns['Other'] += 1
    
    if failures_by_file:
        print("📁 FAILURES BY TEST FILE")
        sorted_files = sorted(failures_by_file.items(), key=lambda x: len(x[1]), reverse=True)
        for file_path, test_failures in sorted_files[:10]:  # Top 10
            print(f"   {file_path}: {len(test_failures)} failures")
        print()
    
    # 3. Error pattern analysis
    if error_patterns:
        print("🔧 ERROR PATTERNS")
        for error_type, count in error_patterns.most_common():
            print(f"   {error_type}: {count}")
        print()
    
    # 4. Specific error analysis
    import_errors = re.findall(r'ImportError: cannot import name [\'"]([^\'"]+)[\'"] from [\'"]([^\'"]+)[\'"]', content)
    if import_errors:
        print("⚠️  IMPORT ERRORS DETECTED")
        print("   Fix: Update imports to match actual class names")
        for name, module in set(import_errors[:5]):
            print(f"   - Cannot import '{name}' from '{module}'")
            print(f"     Check: python -c \"from {module} import {name}\"")
        print()
    
    attribute_errors = re.findall(r"AttributeError: ['\"]?([^'\"]+)['\"]? object has no attribute ['\"]([^'\"]+)['\"]", content)
    if attribute_errors:
        print("⚠️  ATTRIBUTE ERRORS DETECTED")
        print("   Fix: Update mocks to include missing attributes")
        for obj, attr in set(attribute_errors[:5]):
            print(f"   - {obj} missing attribute: {attr}")
        print()
    
    # 5. Most problematic test files
    if failures_by_file:
        print("🎯 TOP 5 PROBLEMATIC TEST FILES")
        for i, (file_path, test_failures) in enumerate(sorted_files[:5], 1):
            print(f"\n   {i}. {file_path} ({len(test_failures)} failures)")
            print(f"      Command: pytest {file_path} -vvs --tb=long")
            
            # Show first 3 failed tests
            for test_name, error in test_failures[:3]:
                print(f"      ❌ {test_name}")
                error_short = error[:80] + "..." if len(error) > 80 else error
                print(f"         {error_short}")
        print()
    
    # 6. Actionable recommendations
    print("💡 RECOMMENDED ACTIONS")
    print()
    
    if error_patterns.get('ImportError', 0) > 10:
        print("   🔴 HIGH PRIORITY: Fix Import Errors")
        print("      1. Run: python -c 'import app.rag.embeddings; print(dir(app.rag.embeddings))'")
        print("      2. Update test imports to match actual class names")
        print("      3. Verify __init__.py files exist in all packages")
        print()
    
    if error_patterns.get('AttributeError', 0) > 10:
        print("   🔴 HIGH PRIORITY: Fix Mock Attribute Errors")
        print("      1. Review mock setup in test files")
        print("      2. Add missing attributes: mock.return_value = MagicMock()")
        print("      3. Check actual class interfaces")
        print()
    
    if 'test_config.py' in [f for f, _ in sorted_files[:5]]:
        print("   🟡 MEDIUM: Fix Configuration Tests")
        print("      1. Mock environment variables")
        print("      2. Mock Secret Manager")
        print("      3. Set default config values")
        print()
    
    if 'test_main.py' in [f for f, _ in sorted_files[:5]]:
        print("   🟡 MEDIUM: Fix Main Application Tests")
        print("      1. Mock all GCP services (Vertex AI, Firestore, etc.)")
        print("      2. Use FastAPI TestClient properly")
        print("      3. Verify async test decorators")
        print()
    
    print("   📚 RESOURCES")
    print("      - Full debugging guide: docs/TEST_DEBUGGING_GUIDE.md")
    print("      - Run locally: pytest tests/unit/ -v --maxfail=5")
    print("      - Debug single test: pytest <path> -vvs --tb=long")
    print()
    
    # 7. Quick fix template
    if import_errors or attribute_errors:
        print("🛠️  QUICK FIX TEMPLATE")
        print()
        print("   # Fix import error:")
        print("   from app.rag.embeddings import VertexTextEmbedder  # Not EmbeddingGenerator")
        print()
        print("   # Fix attribute error:")
        print("   mock_obj = MagicMock()")
        print("   mock_obj.missing_method.return_value = expected_value")
        print()
    
    print("="*70)
    print("💻 NEXT STEPS")
    print("="*70)
    print("1. Fix highest priority errors first (ImportError, AttributeError)")
    print("2. Run locally: pytest <failing_test_file> -vvs --tb=long")
    print("3. Verify fix: pytest <failing_test_file> -v")
    print("4. Commit and push to trigger Cloud Build")
    print("5. Monitor: gcloud builds log <BUILD_ID> --stream")
    print("="*70)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_test_failures.py <log-file>")
        print()
        print("Example:")
        print("  1. Download build log: gcloud builds log <BUILD_ID> > build-log.txt")
        print("  2. Analyze: python scripts/analyze_test_failures.py build-log.txt")
        sys.exit(1)
    
    analyze_test_output(sys.argv[1])
