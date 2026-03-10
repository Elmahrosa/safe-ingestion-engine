# GitHub Actions Setup Guide - Safe Ingestion Engine

## 📋 Pre-Setup Checklist

- [x] Workflow file deployed: `.github/workflows/docker-ci.yml`
- [ ] Docker Hub account created
- [ ] Docker Hub access token generated (with write:packages permission)
- [ ] GitHub Secrets configured (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `SAFE_API_KEY`)
- [ ] Workflow tested on a push

---

## 1️⃣ Create Docker Hub Access Token

**Why?** GitHub Actions needs permission to push images to Docker Hub without using your password.

### Steps:

1. Go to **Docker Hub** → https://hub.docker.com/
2. Click your profile icon → **Account Settings**
3. Left sidebar → **Security** → **New Access Token**
4. Name: `github-actions` (or similar)
5. Permissions: `Read & Write`
6. Click **Generate**
7. Copy the token (you won't see it again)

---

## 2️⃣ Add GitHub Secrets

**Repository:** https://github.com/Elmahrosa/safe-ingestion-engine

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**

### Required Secrets:

| Secret Name | Value | Where to Get |
|-------------|-------|--------------|
| `DOCKER_USERNAME` | Your Docker Hub username | Docker Hub profile → username |
| `DOCKER_PASSWORD` | Your Docker Hub access token | Generated in Step 1 above |

### Optional Secrets (if testing Safe API):

| Secret Name | Value | Notes |
|-------------|-------|-------|
| `SAFE_API_KEY` | Your Safe trial API key | Email from Safe team |

**How to add a secret:**

1. Click **New repository secret**
2. Name: `DOCKER_USERNAME`
3. Value: `yourusername`
4. Click **Add secret**
5. Repeat for `DOCKER_PASSWORD`

---

## 3️⃣ Verify Workflow Configuration

The workflow runs automatically on:

- **Push to `main` branch** → Full pipeline (lint, test, build, publish)
- **Push to `dev` branch** → Full pipeline (no publish)
- **Pull requests to `main`** → Full pipeline (no publish)
- **Tag push** (e.g., `git tag v1.0.0`) → Publish with semantic version

---

## 4️⃣ First Run

### Trigger the workflow:

```bash
# Ensure workflow file is committed
git add .github/workflows/docker-ci.yml
git commit -m "ci: add enterprise Docker CI/CD pipeline"
git push origin main
```

### Monitor the workflow:

1. Go to **GitHub repo** → **Actions** tab
2. Click **Docker CI/CD Pipeline** (latest run)
3. Watch jobs execute in order:
   - ✅ Lint & Type Check
   - ✅ Security Scan
   - ✅ Tests (Python 3.11, 3.12)
   - ✅ Docker Build & Cache
   - ✅ Docker Compose Integration Test
   - ✅ Docker Scout Security Scan
   - ✅ Trivy Container Scan
   - ✅ Build & Publish to Docker Hub
   - ✅ Pipeline Summary

### Expected output:

```
✅ All jobs passed
🐳 Docker image published to: docker.io/yourusername/safe-ingestion-engine:main
📊 Image available as: yourusername/safe-ingestion-engine:latest (on main branch)
```

---

## 5️⃣ Test Docker Image Locally

After the workflow completes and publishes:

```bash
# Pull the newly built image
docker pull yourusername/safe-ingestion-engine:latest

# Verify image metadata
docker inspect yourusername/safe-ingestion-engine:latest

# Run locally
docker run -d \
  -p 8000:8000 \
  -p 8501:8501 \
  -e REDIS_URL=redis://host.docker.internal:6379/0 \
  yourusername/safe-ingestion-engine:latest

# Test endpoints
curl http://localhost:8000/health
```

---

## 6️⃣ Image Tagging Strategy

The workflow auto-generates these tags:

| Trigger | Image Tags |
|---------|-----------|
| Push to `main` | `latest`, `main-<sha>` |
| Push to `dev` | `dev`, `dev-<sha>` |
| Tag `v1.0.0` | `1.0.0`, `1.0`, `v1.0.0` |

**Pull any version:**

```bash
# Latest from main
docker pull yourusername/safe-ingestion-engine:latest

# Specific version
docker pull yourusername/safe-ingestion-engine:1.0.0

# Specific commit
docker pull yourusername/safe-ingestion-engine:main-a1b2c3d
```

---

## 7️⃣ Workflow Jobs Explained

### **Lint & Type Check**
- Runs `ruff` for linting and formatting
- Runs `mypy` for type checking
- **Fails on:** Code style violations, type errors

### **Security Scan**
- Runs `bandit` for code security issues
- Runs `pip-audit` for dependency vulnerabilities
- Checks `.env` is not committed
- **Fails on:** Security issues, CVEs

### **Tests (Python 3.11 & 3.12)**
- Starts Redis service
- Runs full test suite with coverage
- **Fails on:** Test failures, coverage < 60%

### **Docker Build & Cache**
- Builds multi-architecture image (`amd64 + arm64`)
- Uses GitHub Actions cache for speed
- **Fails on:** Build errors

### **Docker Compose Integration Test**
- Spins up full stack (API, Worker, Redis, Dashboard)
- Tests `/health` endpoint
- Tests `/scan` endpoint connectivity
- **Fails on:** Service startup or endpoint failures

### **Docker Scout Security Scan**
- Scans image for vulnerabilities
- Focuses on CRITICAL and HIGH severity
- **Fails on:** Critical vulnerabilities found

### **Trivy Container Scan**
- Deep vulnerability scan using Trivy
- Uploads results to GitHub Security tab
- **Fails on:** Critical vulnerabilities found

### **Build & Publish to Docker Hub**
- Only runs on `main` branch or version tags
- Builds multi-platform image
- Pushes to Docker Hub
- Updates Docker Hub description
- **Fails on:** Docker Hub auth or build errors

### **Pipeline Summary**
- Generates summary report in GitHub Actions
- Shows all job statuses

---

## 🔧 Troubleshooting

### Workflow won't run

**Issue:** No workflow visible in Actions tab
**Fix:**
```bash
git log --oneline .github/workflows/docker-ci.yml
# Should show recent commit
```

If not visible, try:
```bash
git add .github/workflows/docker-ci.yml
git commit --amend --no-edit
git push -f origin main
```

### Docker Hub push fails

**Issue:** `authentication required`
**Fix:**
1. Verify `DOCKER_USERNAME` secret is correct (check Docker Hub username, not email)
2. Verify `DOCKER_PASSWORD` is an access token, not your account password
3. Test locally: `docker login -u yourusername`

### Tests fail due to Redis timeout

**Issue:** `FAILED tests/test_redis.py::test_connection`
**Fix:** Already handled in workflow—Redis has health checks. Check if your test file exists:
```bash
ls tests/
```

### Security scan shows vulnerabilities

**Issue:** Workflow fails at Docker Scout or Trivy step
**Fix:**
- Check the vulnerability details in GitHub Actions logs
- Update dependencies: `pip install --upgrade requests fastapi ...`
- Update base image in Dockerfile: `FROM python:3.12-slim`

### Secrets not working

**Issue:** `The following secrets are undefined: DOCKER_USERNAME`
**Fix:**
1. Verify secrets exist: Go to **Settings** → **Secrets and variables** → **Actions**
2. Check exact spelling (case-sensitive): `DOCKER_USERNAME`, `DOCKER_PASSWORD`
3. If just added, wait 30 seconds for GitHub to sync

---

## 📊 Monitoring

### Check workflow status

```bash
# View latest workflow run
gh run list --workflow=docker-ci.yml --limit=5

# View specific run details
gh run view <RUN_ID> --log
```

### View Docker Hub stats

- Go to https://hub.docker.com/r/yourusername/safe-ingestion-engine
- See pull counts, star count, tags

### View GitHub Security

- Repo → **Security** → **Code scanning alerts**
- Shows vulnerabilities from Trivy scans

---

## ✅ Success Criteria

Your workflow is set up correctly when:

- [x] All jobs pass on first run
- [x] Docker image appears on Docker Hub
- [x] `docker pull yourusername/safe-ingestion-engine:latest` works
- [x] GitHub Secrets are configured
- [x] No security issues flagged

---

## 🚀 Next Steps

1. **Push first commit:** `git push origin main`
2. **Monitor workflow:** Check Actions tab
3. **Pull image:** `docker pull yourusername/safe-ingestion-engine:latest`
4. **Deploy to production:** Use the published image in Kubernetes, Docker Swarm, or VM

---

## 📞 Support

- **Workflow syntax:** https://docs.github.com/en/actions
- **Docker Build action:** https://github.com/docker/build-push-action
- **Docker Scout:** https://docs.docker.com/scout/
- **Trivy:** https://github.com/aquasecurity/trivy-action
