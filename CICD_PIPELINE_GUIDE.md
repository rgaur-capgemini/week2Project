# CI/CD Pipeline: Develop → Main Branch Flow

## Overview

This project uses **Cloud Build** for automated CI/CD with a two-branch strategy:

- **`develop` branch**: Continuous Integration (CI) — Build, Test, Scan, Push
- **`main` branch**: Continuous Deployment (CD) — Build, Test, Scan, Push, **Deploy to GKE**

**GitHub Repository**: https://github.com/rgaur-capgemini/week2Project.git

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Developer Workflow                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Work on feature branch                                      │
│     git checkout -b feature/my-feature                          │
│                                                                 │
│  2. Push to develop                                             │
│     git checkout develop                                        │
│     git merge feature/my-feature                                │
│     git push origin develop                                     │
│        │                                                        │
│        ├──> ⚡ AUTO-TRIGGERS: develop-branch-ci                │
│        │    ✅ Build backend + frontend Docker images          │
│        │    ✅ Run pytest tests with coverage                  │
│        │    ✅ Scan images with Trivy (security)               │
│        │    ✅ Push images to Artifact Registry                │
│        │    ❌ NO GKE deployment                               │
│        │                                                        │
│        └──> ✅ CI passed → Ready for Pull Request              │
│                                                                 │
│  3. Create Pull Request: develop → main                         │
│     On GitHub: Create PR from develop to main                   │
│     Review changes, approve, and merge PR                       │
│        │                                                        │
│        ├──> ⚡ AUTO-TRIGGERS: main-branch-cd                   │
│        │    ✅ Build backend + frontend Docker images          │
│        │    ✅ Run pytest tests with coverage                  │
│        │    ✅ Scan images with Trivy (security)               │
│        │    ✅ Push images to Artifact Registry                │
│        │    ✅ DEPLOY TO GKE CLUSTER (production)              │
│        │                                                        │
│        ├──> Triggers: master-branch-cd                         │
│        │    ✅ Build backend + frontend Docker images          │
│        │    ✅ Run pytest tests with coverage                  │
│        │    ✅ Scan images with Trivy (security)               │
│        │    ✅ Push images to Artifact Registry                │
│        │    ✅ DEPLOY TO GKE CLUSTER (production)              │
│        │                                                        │
│        └──> Production is live! 🚀                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Setup Instructions

### 1. Prerequisites

- GitHub repository connected to Cloud Build
- GCP project: `botpproject`
- GKE cluster: `rag-chatbot-cluster` (us-central1-a)
- Artifact Registry: `us-central1-docker.pkg.dev/botpproject/rag-service`

### 2. Connect GitHub to Cloud Build

```bash
# If not already connected, create a GitHub connection
gcloud builds connections create github my-github-connection \
  --region=us-central1 \
  --project=botpproject

# Follow the OAuth flow to authorize Cloud Build
```

### 3. Create Cloud Build Triggers

**Option A: Run the setup script**

```bash
# 1. Edit setup-cicd-triggers.sh and update:
#    - GITHUB_REPO_OWNER="your-github-username"
#    - GITHUB_REPO_NAME="your-repo-name"

# 2. Run the script
bash setup-cicd-triggers.sh
```

**Option B: Manual trigger creation**

```bash
# Develop branch CI trigger
gcloud builds triggers create github \
  --name="develop-branch-ci" \
  --repo-name="YOUR_REPO_NAME" \
  --repo-owner="YOUR_GITHUB_USERNAME" \
  --branch-pattern="^develop$" \
  --build-config="cloudbuild-gke.yaml" \
  --substitutions="_SKIP_DEPLOY=true" \
  --included-files="app/**,week5/**,frontend/**,k8s/**,requirements.txt,Dockerfile,frontend/Dockerfile" \
  --project=botpproject \
  --region=us-central1 \
  --description="CI for develop branch"

# Master branch CD trigger
gcloud builds triggers create github \
  --name="master-branch-cd" \
  --repo-name="YOUR_REPO_NAME" \
  --repo-owner="YOUR_GITHUB_USERNAME" \
  --branch-pattern="^master$" \
  --build-config="cloudbuild-gke.yaml" \
  --included-files="app/**,week5/**,frontend/**,k8s/**,requirements.txt,Dockerfile,frontend/Dockerfile" \
  --project=botpproject \
  --region=us-central1 \
  --description="Full CD for master branch"
```

### 4. Verify Triggers

```bash
# List all triggers
gcloud builds triggers list --project=botpproject --region=us-central1

# View in console
https://console.cloud.google.com/cloud-build/triggers?project=botpproject
```

---

## Build Pipeline Details

### File Used: `cloudbuild-gke.yaml`

This single YAML file handles **both** develop and master builds. The deployment steps are conditionally executed based on the branch.

**Pipeline Steps:**

| Step | Develop Branch | Main Branch | Description |
|---|---|---|---|
| 1. Build Backend | ✅ | ✅ | Builds `rag-service` Docker image |
| 2. Test Backend | ✅ | ✅ | Runs `pytest` with coverage |
| 3. Scan Backend | ✅ | ✅ | Trivy security scan |
| 4. Push Backend | ✅ | ✅ | Push to Artifact Registry |
| 5. Build Frontend | ✅ | ✅ | Builds Angular frontend image |
| 6. Scan Frontend | ✅ | ✅ | Trivy security scan |
| 7. Push Frontend | ✅ | ✅ | Push to Artifact Registry |
| 8. Get GKE Credentials | ❌ | ✅ | Authenticate to GKE |
| 9. Deploy Backend | ❌ | ✅ | Update `rag-backend` deployment |
| 10. Deploy Frontend | ❌ | ✅ | Update `rag-frontend` deployment |
| 11. Rollout Status | ❌ | ✅ | Wait for successful rollout |

---

## Week5 Code Integration

### Structure

```
week3_btoproject_cloudrun_full/
├── app/                    # Core backend (Weeks 1-4)
├── week5/                  # Week 5 features (Agentic AI, Multimodal, CSV, Enhanced RAG)
├── frontend/               # Angular UI
├── k8s/                    # Kubernetes manifests
├── requirements.txt        # Python dependencies (includes week5)
├── Dockerfile              # Backend image (includes week5 code)
├── cloudbuild-gke.yaml     # ⭐ THIS FILE — used for all CI/CD
└── setup-cicd-triggers.sh  # Trigger creation script
```

### How Week5 Code is Built

1. **Backend Dockerfile** includes all week5 modules:
   ```dockerfile
   COPY app/ /app/app/
   COPY week5/ /app/week5/
   COPY requirements.txt /app/
   RUN pip install -r requirements.txt
   ```

2. **`app/main.py`** dynamically imports week5 routes:
   ```python
   try:
       from week5.api.agent_routes import agent_router, rag_router
       from week5.api.multimodal_routes import multimodal_router
       app.include_router(agent_router, prefix="/week5")
       app.include_router(rag_router, prefix="/week5")
       app.include_router(multimodal_router, prefix="/week5")
   except ImportError:
       logger.warning("Week 5 features not available")
   ```

3. **Triggered by changes** to:
   - `app/**` — Core backend
   - `week5/**` — Week 5 code
   - `frontend/**` — Angular UI
   - `requirements.txt` — Dependencies
   - `Dockerfile` — Build changes

---

## Branch Strategy

### Develop Branch

**Purpose**: Integration testing, CI validation

**Workflow**:
```bash
# Create feature
git checkout -b feature/new-api develop
# ... make changes ...
git add .
git commit -m "feat: add new API endpoint"

# Push to develop
git checkout develop
git merge feature/new-api
git push origin develop

# ⚡ AUTO-TRIGGERED: develop-branch-ci pipeline runs
# ✅ Cloud Build runs CI pipeline
# ⏳ Wait for build to pass
# 🔍 Review logs: https://console.cloud.google.com/cloud-build/builds?project=botpproject
```

**Build Output**: Images tagged as `$COMMIT_SHA` and `latest` in Artifact Registry

### Main Branch

**Purpose**: Production deployment

**Workflow**:
```bash
# After develop build passes
# 1. Go to GitHub → Create Pull Request
#    Base: main ← Compare: develop

# 2. Review changes, approve, and merge PR on GitHub UI

# OR via CLI:
git checkout main
git merge develop
git push origin main

# ⚡ AUTO-TRIGGERED: main-branch-cd pipeline runs
# ✅ Cloud Build runs full CD pipeline
# 🚀 Auto-deploys to GKE cluster
# 🔍 Monitor: kubectl get pods -n default
```

**Build Output**: Images deployed to GKE with tag `$COMMIT_SHA`

---

## Monitoring & Troubleshooting

### View Build Status

```bash
# List recent builds
gcloud builds list --project=botpproject --limit=10

# View specific build
gcloud builds log BUILD_ID --project=botpproject
```

### Console Links

- **Builds**: https://console.cloud.google.com/cloud-build/builds?project=botpproject
- **Triggers**: https://console.cloud.google.com/cloud-build/triggers?project=botpproject
- **Artifact Registry**: https://console.cloud.google.com/artifacts/docker/botpproject/us-central1/rag-service?project=botpproject
- **GKE Cluster**: https://console.cloud.google.com/kubernetes/clusters/details/us-central1-a/rag-chatbot-cluster?project=botpproject

### Common Issues

**Issue 1: Build fails on develop**
- Check test results: Review pytest output in Cloud Build logs
- Fix locally: `pytest tests/ -v`
- Repush to develop

**Issue 2: Deployment fails on master**
- Check GKE cluster status: `kubectl get nodes`
- Check deployment: `kubectl describe deployment rag-backend`
- Check logs: `kubectl logs -l app=rag-backend --tail=100`

**Issue 3: Trigger not firing**
- Verify included files pattern matches your changes
- Check trigger status: `gcloud builds triggers describe develop-branch-ci --region=us-central1 --project=botpproject`
- Manually trigger: Cloud Console → Cloud Build → Triggers → Run

---

## Manual Trigger (Testing)

```bash
# Trigger develop pipeline manually
gcloud builds triggers run develop-branch-ci --branch=develop --project=botpproject

# Trigger master pipeline manually
gcloud builds triggers run master-branch-cd --branch=master --project=botpproject
```

---

## Admin Access Configuration

**Admin Role**: `raman.gaur@capgemini.com`

All other users can:
- ✅ Chat with RAG bot
- ✅ Upload compliance documents
- ✅ View chat history
- ✅ Use Week 5 features (Agentic AI, Multimodal, CSV ingestion)

Only `raman.gaur@capgemini.com` can:
- ✅ Access `/admin` dashboard
- ✅ Access `/finops` dashboard
- ✅ View system analytics
- ✅ Manage A/B experiments
- ✅ View cost optimization reports

**Configuration Files**:
- `app/config.py`: `ADMIN_EMAILS = ["raman.gaur@capgemini.com"]`
- `k8s/backend-deployment.yaml`: `ADMIN_EMAILS` env var
- `.env.template`: Default admin email

---

## Summary

✅ **Two-branch CI/CD pipeline configured**
✅ **Develop**: CI only (build, test, scan, push)
✅ **Master**: Full CD (build, test, scan, push, deploy to GKE)
✅ **Week5 code** automatically included in builds
✅ **Admin access** limited to `raman.gaur@capgemini.com`
✅ **All users** can login with Google OAuth and use the chatbot

**Next Steps**:
1. Update `setup-cicd-triggers.sh` with your GitHub repo details
2. Run `bash setup-cicd-triggers.sh`
3. Push to develop → verify CI passes
4. Merge to master → verify production deployment

🚀 **Happy deploying!**
