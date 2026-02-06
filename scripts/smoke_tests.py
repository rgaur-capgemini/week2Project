"""
Smoke tests to verify deployment is working correctly.
Run after deployment to GKE to validate all endpoints.
"""

import requests
import sys
import os

# Get base URL from environment or use default
BASE_URL = os.getenv('APP_URL', 'http://localhost:8080')


def test_health():
    """Test health endpoint."""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'
    print("✅ Health check passed")


def test_readiness():
    """Test readiness endpoint."""
    print("Testing readiness endpoint...")
    response = requests.get(f"{BASE_URL}/readiness")
    assert response.status_code == 200
    data = response.json()
    assert 'ready' in data
    print("✅ Readiness check passed")


def test_api_endpoints_without_auth():
    """Test that protected endpoints return 401 without auth."""
    print("Testing authentication requirement...")
    
    # These should require authentication
    protected_endpoints = [
        '/api/v1/chat/query',
        '/api/v1/chat/sessions',
        '/api/v1/admin/analytics/usage'
    ]
    
    for endpoint in protected_endpoints:
        response = requests.get(f"{BASE_URL}{endpoint}")
        # Should get 401 or 403 (unauthorized/forbidden)
        assert response.status_code in [401, 403], \
            f"Endpoint {endpoint} should require authentication"
    
    print("✅ Authentication requirement verified")


def run_smoke_tests():
    """Run all smoke tests."""
    print(f"Running smoke tests against {BASE_URL}")
    print("=" * 60)
    
    try:
        test_health()
        test_readiness()
        test_api_endpoints_without_auth()
        
        print("=" * 60)
        print("✅ All smoke tests passed!")
        return 0
    
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        return 1
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        print(f"Could not connect to {BASE_URL}")
        return 1
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(run_smoke_tests())
