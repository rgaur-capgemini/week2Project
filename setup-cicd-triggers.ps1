# Setup Cloud Build Triggers for Develop → Main CI/CD Pipeline
# PowerShell version for Windows
#
# USAGE: Run this script in PowerShell after connecting GitHub to Cloud Build

$ErrorActionPreference = "Stop"

$PROJECT_ID = "botpproject"
$REGION = "us-central1"
$GITHUB_REPO_OWNER = "rgaur-capgemini"
$GITHUB_REPO_NAME = "week2Project"

Write-Host ""
Write-Host "=========================================="
Write-Host "Cloud Build Triggers Setup"
Write-Host "=========================================="
Write-Host ""
Write-Host "Project:  $PROJECT_ID"
Write-Host "Region:   $REGION"
Write-Host "GitHub:   https://github.com/$GITHUB_REPO_OWNER/$GITHUB_REPO_NAME"
Write-Host ""

# ============================================================================
# Check GitHub Connection
# ============================================================================
Write-Host "==> Checking GitHub connection..." -ForegroundColor Cyan
$connections = gcloud builds connections list --region=$REGION --project=$PROJECT_ID --format=json 2>&1 | ConvertFrom-Json

if ($connections.Count -eq 0) {
    Write-Host ""
    Write-Host "⚠️  No GitHub connection found!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please connect GitHub first:"
    Write-Host "  1. Go to: https://console.cloud.google.com/cloud-build/triggers/connect?project=$PROJECT_ID&region=$REGION"
    Write-Host "  2. Click 'Connect Repository'"
    Write-Host "  3. Select 'GitHub' and authorize Cloud Build"
    Write-Host "  4. Select repository: $GITHUB_REPO_OWNER/$GITHUB_REPO_NAME"
    Write-Host "  5. Re-run this script"
    Write-Host ""
    
    $response = Read-Host "Open the connection page now? (y/n)"
    if ($response -eq "y") {
        Start-Process "https://console.cloud.google.com/cloud-build/triggers/connect?project=$PROJECT_ID&region=$REGION"
    }
    exit 1
}

Write-Host "✅ GitHub connection found!" -ForegroundColor Green
Write-Host ""

# ============================================================================
# Trigger 1: DEVELOP Branch (CI Only)
# ============================================================================
Write-Host "==> Creating DEVELOP branch CI trigger..." -ForegroundColor Cyan

gcloud builds triggers create github `
  --name="develop-branch-ci" `
  --repo-name="$GITHUB_REPO_NAME" `
  --repo-owner="$GITHUB_REPO_OWNER" `
  --branch-pattern="^develop$" `
  --build-config="cloudbuild-gke.yaml" `
  --substitutions="_SKIP_DEPLOY=true" `
  --included-files="app/**,week5/**,frontend/**,k8s/**,requirements.txt,Dockerfile,frontend/Dockerfile" `
  --project="$PROJECT_ID" `
  --region="$REGION" `
  --description="CI pipeline for develop branch - builds, tests, scans, and pushes images (no GKE deploy)"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Develop branch trigger created successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to create develop branch trigger" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ============================================================================
# Trigger 2: MAIN Branch (Full CD)
# ============================================================================
Write-Host "==> Creating MAIN branch CD trigger..." -ForegroundColor Cyan

gcloud builds triggers create github `
  --name="main-branch-cd" `
  --repo-name="$GITHUB_REPO_NAME" `
  --repo-owner="$GITHUB_REPO_OWNER" `
  --branch-pattern="^main$" `
  --build-config="cloudbuild-gke.yaml" `
  --included-files="app/**,week5/**,frontend/**,k8s/**,requirements.txt,Dockerfile,frontend/Dockerfile" `
  --project="$PROJECT_ID" `
  --region="$REGION" `
  --description="Full CD pipeline for main branch - builds, tests, scans, pushes images, and deploys to GKE"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Main branch trigger created successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to create main branch trigger" -ForegroundColor Red
    exit 1
}

# ============================================================================
# Summary
# ============================================================================
Write-Host ""
Write-Host "=========================================="
Write-Host "✅ CI/CD Triggers Created Successfully!"
Write-Host "=========================================="
Write-Host ""
Write-Host "📋 Trigger Summary:" -ForegroundColor Cyan
Write-Host "  1. develop-branch-ci  → Runs on every push to 'develop'"
Write-Host "     ✅ Builds Docker images"
Write-Host "     ✅ Runs pytest tests"
Write-Host "     ✅ Scans with Trivy"
Write-Host "     ✅ Pushes to Artifact Registry"
Write-Host "     ❌ Does NOT deploy to GKE"
Write-Host ""
Write-Host "  2. main-branch-cd     → Runs on every push to 'main'"
Write-Host "     ✅ Builds Docker images"
Write-Host "     ✅ Runs pytest tests"
Write-Host "     ✅ Scans with Trivy"
Write-Host "     ✅ Pushes to Artifact Registry"
Write-Host "     ✅ Deploys to GKE cluster"
Write-Host ""
Write-Host "🔄 Workflow:" -ForegroundColor Cyan
Write-Host "  1. Push to 'develop' → CI builds and tests"
Write-Host "  2. Create PR: 'develop' → 'main' → Full deployment to production GKE"
Write-Host "  3. GitHub repo: https://github.com/$GITHUB_REPO_OWNER/$GITHUB_REPO_NAME"
Write-Host ""
Write-Host "View triggers: https://console.cloud.google.com/cloud-build/triggers?project=$PROJECT_ID" -ForegroundColor Cyan
Write-Host ""

# List all triggers
Write-Host "==> Current triggers:" -ForegroundColor Cyan
gcloud builds triggers list --project=$PROJECT_ID --region=$REGION

Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
