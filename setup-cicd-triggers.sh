#!/bin/bash
# Setup Cloud Build Triggers for Develop → Master CI/CD Pipeline
# 
# USAGE:
#   1. Update the GITHUB_REPO_OWNER and GITHUB_REPO_NAME below
#   2. Run: bash setup-cicd-triggers.sh
#   3. OR run commands manually after updating values

set -e

PROJECT_ID="botpproject"
REGION="us-central1"

# ============================================================================
# GitHub Repository Configuration
# ============================================================================
GITHUB_REPO_OWNER="rgaur-capgemini"
GITHUB_REPO_NAME="week2Project"

# ============================================================================
# Validate GitHub Connection
# ============================================================================
echo "==> Checking GitHub App connection..."
gcloud builds connections list --region="$REGION" --project="$PROJECT_ID"

echo ""
echo "If you don't see a GitHub connection above, connect GitHub first:"
echo "  gcloud builds connections create github CONNECTION_NAME --region=$REGION --project=$PROJECT_ID"
echo ""
read -p "Press Enter to continue with trigger setup..."

# ============================================================================
# Trigger 1: DEVELOP Branch (CI Only - Build + Test, NO Deploy)
# ============================================================================
echo ""
echo "==> Creating DEVELOP branch CI trigger..."
gcloud builds triggers create github \
  --name="develop-branch-ci" \
  --repo-name="$GITHUB_REPO_NAME" \
  --repo-owner="$GITHUB_REPO_OWNER" \
  --branch-pattern="^develop$" \
  --build-config="cloudbuild-gke.yaml" \
  --substitutions="_SKIP_DEPLOY=true" \
  --included-files="app/**,week5/**,frontend/**,k8s/**,requirements.txt,Dockerfile,frontend/Dockerfile" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --description="CI pipeline for develop branch - builds, tests, scans, and pushes images (no GKE deploy)"

echo "✅ Develop branch trigger created successfully!"

# ============================================================================
# Trigger 2: MAIN Branch (Full CD - Build + Test + Deploy to GKE)
# ============================================================================
echo ""
echo "==> Creating MAIN branch CD trigger..."
gcloud builds triggers create github \
  --name="main-branch-cd" \
  --repo-name="$GITHUB_REPO_NAME" \
  --repo-owner="$GITHUB_REPO_OWNER" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild-gke.yaml" \
  --included-files="app/**,week5/**,frontend/**,k8s/**,requirements.txt,Dockerfile,frontend/Dockerfile" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --description="Full CD pipeline for main branch - builds, tests, scans, pushes images, and deploys to GKE"

echo "✅ Main branch trigger created successfully!"

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "=========================================="
echo "CI/CD Triggers Created Successfully!"
echo "=========================================="
echo ""
echo "📋 Trigger Summary:"
echo "  1. develop-branch-ci  → Runs on every push to 'develop'"
echo "     - Builds Docker images"
echo "     - Runs pytest tests"
echo "     - Scans with Trivy"
echo "     - Pushes to Artifact Registry"
echo "     - ❌ Does NOT deploy to GKE"
echo ""
echo "  2. main-branch-cd     → Runs on every push to 'main'"
echo "     - Builds Docker images"
echo "     - Runs pytest tests"
echo "     - Scans with Trivy"
echo "     - Pushes to Artifact Registry"
echo "     - ✅ Deploys to GKE cluster"
echo ""
echo "🔄 Workflow:"
echo "  1. Push to 'develop' → CI builds and tests"
echo "  2. Create PR: 'develop' → 'main' → Full deployment to production GKE"
echo "  3. GitHub repo: https://github.com/rgaur-capgemini/week2Project.git"
echo ""
echo "View triggers: https://console.cloud.google.com/cloud-build/triggers?project=$PROJECT_ID"
echo ""
