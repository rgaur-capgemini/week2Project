#!/bin/bash
# Coverage Check Script - Validates test coverage meets requirements
# Usage: ./scripts/check-coverage.sh

set -e

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Coverage thresholds
BACKEND_LINE_THRESHOLD=80
BACKEND_BRANCH_THRESHOLD=70
FRONTEND_LINE_THRESHOLD=80
FRONTEND_BRANCH_THRESHOLD=70

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Test Coverage Validation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ==================== Backend Coverage ====================
echo -e "${YELLOW}Checking Backend Coverage...${NC}"

# Install dependencies
echo "Installing backend dependencies..."
cd "$(dirname "$0")/.."
pip install -q -r requirements.txt
pip install -q pytest pytest-cov pytest-mock pytest-asyncio 2>/dev/null || true

# Run backend tests with coverage
echo "Running backend tests..."
python -m pytest \
  --cov=app \
  --cov-report=html:coverage-reports/html \
  --cov-report=xml:coverage-reports/coverage.xml \
  --cov-report=term-missing \
  --cov-branch \
  --cov-config=.coveragerc \
  > /tmp/backend-coverage.txt 2>&1 || true

# Parse coverage from output
if [ -f "/tmp/backend-coverage.txt" ]; then
  # Extract line coverage
  BACKEND_LINE_COV=$(grep "TOTAL" /tmp/backend-coverage.txt | awk '{print $4}' | sed 's/%//' || echo "0")
  
  # Extract branch coverage from detailed report
  BACKEND_BRANCH_COV=$(grep "TOTAL" /tmp/backend-coverage.txt | awk '{print $5}' | sed 's/%//' || echo "0")
  
  # Fallback to HTML report if command line parsing fails
  if [ "$BACKEND_LINE_COV" == "0" ] || [ -z "$BACKEND_LINE_COV" ]; then
    BACKEND_LINE_COV=$(grep -oP 'pc_cov">\K[0-9]+' coverage-reports/html/index.html 2>/dev/null | head -1 || echo "0")
  fi
  
  echo ""
  echo -e "${BLUE}Backend Coverage Results:${NC}"
  echo "Line Coverage:   ${BACKEND_LINE_COV}% (Required: ≥${BACKEND_LINE_THRESHOLD}%)"
  echo "Branch Coverage: ${BACKEND_BRANCH_COV}% (Required: ≥${BACKEND_BRANCH_THRESHOLD}%)"
  
  # Check if thresholds met
  BACKEND_LINE_PASS=false
  BACKEND_BRANCH_PASS=false
  
  if (( $(echo "$BACKEND_LINE_COV >= $BACKEND_LINE_THRESHOLD" | bc -l) )); then
    echo -e "${GREEN}✓ Backend Line Coverage: PASS${NC}"
    BACKEND_LINE_PASS=true
  else
    echo -e "${RED}✗ Backend Line Coverage: FAIL${NC}"
  fi
  
  if (( $(echo "$BACKEND_BRANCH_COV >= $BACKEND_BRANCH_THRESHOLD" | bc -l) )); then
    echo -e "${GREEN}✓ Backend Branch Coverage: PASS${NC}"
    BACKEND_BRANCH_PASS=true
  else
    echo -e "${RED}✗ Backend Branch Coverage: FAIL${NC}"
  fi
else
  echo -e "${RED}✗ Could not read backend coverage report${NC}"
  BACKEND_LINE_PASS=false
  BACKEND_BRANCH_PASS=false
fi

echo ""

# ==================== Frontend Coverage ====================
echo -e "${YELLOW}Checking Frontend Coverage...${NC}"

cd frontend

# Install dependencies
echo "Installing frontend dependencies..."
npm install --silent 2>/dev/null || npm install

# Run frontend tests with coverage
echo "Running frontend tests..."
npm run test:ci --silent 2>/dev/null || npm run test:coverage -- --watch=false --browsers=ChromeHeadless --silent 2>/dev/null || true

# Parse coverage from JSON summary
if [ -f "coverage/chatbot-rag-frontend/coverage-summary.json" ]; then
  FRONTEND_LINE_COV=$(node -p "const cov = require('./coverage/chatbot-rag-frontend/coverage-summary.json'); cov.total.lines.pct.toFixed(2)" 2>/dev/null || echo "0")
  FRONTEND_BRANCH_COV=$(node -p "const cov = require('./coverage/chatbot-rag-frontend/coverage-summary.json'); cov.total.branches.pct.toFixed(2)" 2>/dev/null || echo "0")
  
  echo ""
  echo -e "${BLUE}Frontend Coverage Results:${NC}"
  echo "Line Coverage:   ${FRONTEND_LINE_COV}% (Required: ≥${FRONTEND_LINE_THRESHOLD}%)"
  echo "Branch Coverage: ${FRONTEND_BRANCH_COV}% (Required: ≥${FRONTEND_BRANCH_THRESHOLD}%)"
  
  # Check if thresholds met
  FRONTEND_LINE_PASS=false
  FRONTEND_BRANCH_PASS=false
  
  if (( $(echo "$FRONTEND_LINE_COV >= $FRONTEND_LINE_THRESHOLD" | bc -l) )); then
    echo -e "${GREEN}✓ Frontend Line Coverage: PASS${NC}"
    FRONTEND_LINE_PASS=true
  else
    echo -e "${RED}✗ Frontend Line Coverage: FAIL${NC}"
  fi
  
  if (( $(echo "$FRONTEND_BRANCH_COV >= $FRONTEND_BRANCH_THRESHOLD" | bc -l) )); then
    echo -e "${GREEN}✓ Frontend Branch Coverage: PASS${NC}"
    FRONTEND_BRANCH_PASS=true
  else
    echo -e "${RED}✗ Frontend Branch Coverage: FAIL${NC}"
  fi
else
  echo -e "${RED}✗ Could not read frontend coverage report${NC}"
  FRONTEND_LINE_PASS=false
  FRONTEND_BRANCH_PASS=false
fi

cd ..

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Coverage Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Generate summary table
echo "Component     | Line Coverage | Branch Coverage | Status"
echo "------------- | ------------- | --------------- | ------"

BACKEND_STATUS="${GREEN}PASS${NC}"
if [ "$BACKEND_LINE_PASS" = false ] || [ "$BACKEND_BRANCH_PASS" = false ]; then
  BACKEND_STATUS="${RED}FAIL${NC}"
fi

FRONTEND_STATUS="${GREEN}PASS${NC}"
if [ "$FRONTEND_LINE_PASS" = false ] || [ "$FRONTEND_BRANCH_PASS" = false ]; then
  FRONTEND_STATUS="${RED}FAIL${NC}"
fi

echo -e "Backend       | ${BACKEND_LINE_COV}%         | ${BACKEND_BRANCH_COV}%           | ${BACKEND_STATUS}"
echo -e "Frontend      | ${FRONTEND_LINE_COV}%         | ${FRONTEND_BRANCH_COV}%           | ${FRONTEND_STATUS}"

echo ""
echo -e "${BLUE}Coverage Reports:${NC}"
echo "Backend:  coverage-reports/html/index.html"
echo "Frontend: frontend/coverage/chatbot-rag-frontend/index.html"
echo ""

# Final result
if [ "$BACKEND_LINE_PASS" = true ] && [ "$BACKEND_BRANCH_PASS" = true ] && \
   [ "$FRONTEND_LINE_PASS" = true ] && [ "$FRONTEND_BRANCH_PASS" = true ]; then
  echo -e "${GREEN}========================================${NC}"
  echo -e "${GREEN}   ✓ ALL COVERAGE REQUIREMENTS MET${NC}"
  echo -e "${GREEN}========================================${NC}"
  exit 0
else
  echo -e "${RED}========================================${NC}"
  echo -e "${RED}   ✗ COVERAGE REQUIREMENTS NOT MET${NC}"
  echo -e "${RED}========================================${NC}"
  echo ""
  echo -e "${YELLOW}To improve coverage:${NC}"
  echo "1. Add unit tests for uncovered modules"
  echo "2. Add integration tests for complex workflows"
  echo "3. Test edge cases and error handling"
  echo "4. Review coverage reports for specific gaps"
  exit 1
fi
