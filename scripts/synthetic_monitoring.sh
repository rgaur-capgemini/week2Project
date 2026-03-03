#!/bin/bash
# Synthetic monitoring for RAG chatbot endpoints

set -e

PROJECT_ID="${PROJECT_ID:-btoproject-486405}"
BACKEND_URL="${BACKEND_URL:-http://rag-backend-service}"
ALERT_EMAIL="${ALERT_EMAIL:-sre-team@company.com}"

echo "=========================================="
echo "Synthetic Monitoring - RAG Chatbot"
echo "$(date)"
echo "=========================================="

# Function to check endpoint
check_endpoint() {
    local url=$1
    local expected_status=$2
    local endpoint_name=$3
    
    echo "Checking $endpoint_name..."
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" || echo "000")
    
    if [ "$response" -eq "$expected_status" ]; then
        echo "✓ $endpoint_name: OK (HTTP $response)"
        return 0
    else
        echo "✗ $endpoint_name: FAILED (HTTP $response, expected $expected_status)"
        return 1
    fi
}

# Health checks
check_endpoint "$BACKEND_URL/health" 200 "Health Check" || exit 1
check_endpoint "$BACKEND_URL/readiness" 200 "Readiness Check" || exit 1

# Functional test: Query endpoint
echo ""
echo "Testing query endpoint..."
query_response=$(curl -s -X POST "$BACKEND_URL/query" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is RAG?","top_k":3}' 2>/dev/null || echo "{}")

if echo "$query_response" | grep -q "answer"; then
    echo "✓ Query endpoint: OK"
else
    echo "✗ Query endpoint: FAILED"
    echo "Response: $query_response"
    exit 1
fi

# Performance test: Latency check
echo ""
echo "Testing response latency..."
start_time=$(date +%s%3N)
curl -s -X POST "$BACKEND_URL/query" \
  -H "Content-Type: application/json" \
  -d '{"question":"Test","top_k":3}' > /dev/null 2>&1 || true
end_time=$(date +%s%3N)
latency=$((end_time - start_time))

if [ "$latency" -lt 3000 ]; then
    echo "✓ Latency: ${latency}ms (OK)"
else
    echo "⚠ Latency: ${latency}ms (WARNING - exceeds 3s)"
fi

echo ""
echo "=========================================="
echo "All checks passed!"
echo "=========================================="
