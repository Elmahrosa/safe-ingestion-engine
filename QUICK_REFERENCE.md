# Quick Reference Card - Safe Ingestion Engine CI/CD

## 🚀 3-STEP SETUP

### 1. Add GitHub Secrets
```
Repo → Settings → Secrets and variables → Actions
→ New secret: DOCKERHUB_USERNAME
→ New secret: DOCKERHUB_TOKEN (write:packages permission)
→ New secret: SAFE_API_KEY (optional)
```

**Get DOCKERHUB_TOKEN:**
- hub.docker.com → Profile → Account Settings → Security
- New Access Token → Copy → Paste in GitHub Secret

### 2. Push Workflow
```bash
git add .github/workflows/docker-ci.yml
git commit -m "Add production CI/CD pipeline with multi-platform builds"
git push origin main
```

### 3. Monitor
```
Repo → Actions tab
→ Watch "Docker CI/CD Pipeline"
→ After 45 minutes: Image on Docker Hub
```

---

## 📋 PIPELINE STAGES

1. **Lint & Type Check** (2 min)
   - Ruff, Mypy
   - Fails on: Code style violations, type errors

2. **Security Scan** (3 min)
   - Bandit, pip-audit, secret check
   - Fails on: CVEs, hardcoded secrets

3. **Tests** (5 min)
   - pytest, Python 3.11 & 3.12
   - Fails on: Test failures, coverage < 60%

4. **Docker Build** (8 min)
   - Multi-arch (amd64 + arm64)
   - Fails on: Build errors

5. **Docker Compose Tests** (6 min)
   - /health, /scan endpoints
   - Fails on: Service startup errors

6. **Docker Scout** (3 min)
   - Quick vulnerability scan
   - Fails on: Critical vulnerabilities

7. **Trivy** (4 min)
   - Deep CVE analysis
   - Fails on: Critical vulnerabilities

8. **Docker Hub Publish** (10 min)
   - Only on main branch
   - Tags: latest, main, commit-sha, version

9. **Summary Report** (1 min)
   - Job status dashboard

---

## 🔑 GITHUB SECRETS

| Name | Value |
|------|-------|
| `DOCKERHUB_USERNAME` | Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token (write:packages) |
| `SAFE_API_KEY` | Safe trial API key (optional) |

---

## 📦 IMAGE TAGS

```
yourusername/safe-ingestion-engine:latest
yourusername/safe-ingestion-engine:main
yourusername/safe-ingestion-engine:main-a1b2c3d
yourusername/safe-ingestion-engine:1.0.0
```

Pull: `docker pull yourusername/safe-ingestion-engine:latest`

---

## 🎯 DEPLOYMENT

### Docker Compose
```bash
docker compose up -d
curl http://localhost:8000/health
```

### Single Server
```bash
docker pull yourusername/safe-ingestion-engine:latest
docker run -d -p 8000:8000 --env-file .env yourusername/safe-ingestion-engine:latest
```

### Kubernetes
```bash
kubectl apply -f deployment.yaml
```

---

## ✅ SECURITY GATES

Pipeline fails if:
- ❌ Code style violations
- ❌ Type errors
- ❌ Security issues (Bandit)
- ❌ CVEs in dependencies
- ❌ .env file committed
- ❌ Tests fail
- ❌ Service health check fails
- ❌ Critical vulnerabilities found

---

## 📚 DOCUMENTATION

| File | Purpose |
|------|---------|
| `README_CI_CD_SETUP.md` | Overview (5 min) |
| `SECRETS_REFERENCE.md` | Secret setup |
| `GITHUB_ACTIONS_SETUP.md` | Configuration guide |
| `DEPLOYMENT.md` | Deploy options |
| `CI_CD_SUMMARY.md` | Feature details |
| `COMPLETE_SETUP.md` | Full summary |

---

## 🆘 TROUBLESHOOTING

### Secrets not working
- Check exact spelling (case-sensitive): `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`
- Verify `DOCKERHUB_TOKEN` has `write:packages` permission
- Wait 30 seconds for GitHub to sync

### Docker Hub push fails
- Verify `DOCKERHUB_USERNAME` is username, not email
- Verify `DOCKERHUB_TOKEN` is valid access token, not password
- Test locally: `docker login -u yourusername`

### Tests fail
- Check pytest output in Actions logs
- Verify .env.example has required vars
- Check Redis service is healthy

### Vulnerabilities found
- Check Scout/Trivy output in Actions logs
- Update base image: `FROM python:3.12-slim`
- Update dependencies: `pip install --upgrade <package>`

---

## 🔗 USEFUL LINKS

- **Workflow file:** `.github/workflows/docker-ci.yml`
- **Docker Compose:** `docker-compose.yml`
- **Dockerfile:** `Dockerfile`
- **GitHub Secrets:** https://github.com/Elmahrosa/safe-ingestion-engine/settings/secrets/actions
- **GitHub Actions:** https://github.com/Elmahrosa/safe-ingestion-engine/actions
- **Docker Hub:** https://hub.docker.com/r/yourusername/safe-ingestion-engine

---

## ⏱️ TYPICAL RUNTIME

- Full pipeline: **40-50 minutes**
- Lint & tests: **10 minutes** (parallel)
- Build & scan: **15 minutes** (parallel)
- Publish: **10 minutes**

Parallel jobs reduce total time vs sequential.

---

## 🎉 SUCCESS INDICATORS

✅ All jobs show green checkmarks
✅ Image appears on Docker Hub
✅ Image supports amd64 + arm64
✅ Tags are correct (latest, main, etc.)
✅ Docker Hub description updated
✅ No security vulnerabilities found

---

## 📝 WHAT TO DO WITH SAFE_API_KEY

Once you receive the trial key from teosegypt.com:

1. Add `SAFE_API_KEY` secret to GitHub
2. Test locally:
```bash
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-your-key" \
  -d '{"urls": ["https://httpbin.org/json"], "scrub_pii": true}'
```

3. Expected: Forwards to `https://safe.teosegypt.com/v1/ingest_async`

---

**NEXT STEP:** Add secrets to GitHub and push!

```bash
# Test locally first
docker compose up -d
curl http://localhost:8000/health

# Then push to trigger workflow
git push origin main
```
