# Quick Reference: CI/CD Setup

## ✅ GitHub Repository

- **Repo**: https://github.com/rgaur-capgemini/week2Project.git
- **Owner**: rgaur-capgemini
- **Branches**: `develop` (CI) → `main` (CD)

## ✅ Files Updated

| File | Change |
|---|---|
| `cloudbuild-gke.yaml` | Updated to `botpproject`, added branch-based deployment logic |
| `setup-cicd-triggers.sh` | Script to create Cloud Build triggers |
| `CICD_PIPELINE_GUIDE.md` | Complete documentation |

## 🚀 Quick Start

### 1. Update GitHub Repo Details

Edit `setup-cicd-triggers.sh`:
```bash
GITHUB_REPO_OWNER="YOUR_GITHUB_USERNAME"  # e.g., "ramgaur"
GITHUB_REPO_NAME="YOUR_REPO_NAME"         # e.g., "week3-chatbot"
```

### 2. Run Setup

```bash
bash setup-cicd-triggers.sh
```

### 3. Verify

```bash
gcloud builds triggers list --project=botpproject --region=us-central1
```

## 📋 What Gets Triggered

| Branch | Trigger | Actions |
|---|---|---|
| `develop` | `develop-branch-ci` | Build → Test → Scan → Push (NO Deploy) |
| `main` | `main-branch-cd` | Build → Test → Scan → Push → **Deploy to GKE** |

## 🔄 Developer Workflow

```bash
# 1. Work on feature
git checkout -b feature/new-endpoint develop
# ... code changes ...
git add .
git commit -m "feat: add new endpoint"

# 2. Push to develop — AUTO-TRIGGERS CI
git checkout develop
git merge feature/new-endpoint
git push origin develop
# ⚡ Cloud Build CI runs automatically
# ⏳ Wait for CI to pass

# 3. Create Pull Request on GitHub
#    develop → main
#    Review, approve, and merge PR

# 4. Merge triggers production deployment
#    ⚡ Cloud Build CD runs automatically
#    🚀 Auto-deploys to GKE!

# Check deployment status:
kubectl get pods -n default
kubectl rollout status deployment/rag-backend
```

## 🔍 Monitor Builds

- Console: https://console.cloud.google.com/cloud-build/builds?project=botpproject
- CLI: `gcloud builds list --project=botpproject --limit=5`

## 👤 Admin Access

- **Admin**: `raman.gaur@capgemini.com` (full access to /admin and /finops)
- **All Users**: Can login via Google OAuth and use the chatbot

## 📦 What Gets Built

- Backend image: `us-central1-docker.pkg.dev/botpproject/rag-service/rag-service`
- Frontend image: `us-central1-docker.pkg.dev/botpproject/rag-service/rag-frontend`
- Includes: `app/` (Weeks 1-4) + `week5/` (Agentic AI, Multimodal, CSV, Enhanced RAG)

---

**Need help?** See `CICD_PIPELINE_GUIDE.md` for full documentation.
