# GitHub Actions Secrets Reference

## 🔑 Required Secrets

Add these to: **Settings → Secrets and variables → Actions**

### DOCKERHUB_USERNAME
**Value:** Your Docker Hub username
**Where to find:** https://hub.docker.com/ → Profile icon → Docker Hub username

**Example:**
```
DOCKERHUB_USERNAME = elmahrosa
```

### DOCKERHUB_TOKEN
**Value:** Docker Hub access token (NOT your account password)
**Permissions needed:** `read:packages`, `write:packages`, `delete:packages`
**Where to find:** https://hub.docker.com/ → Profile icon → Account Settings → Security → New Access Token

**Steps to generate:**
1. Log in to Docker Hub
2. Click profile icon → Account Settings
3. Left sidebar → Security
4. Click "New Access Token"
5. Name: `github-actions`
6. Permissions: Select `read:packages`, `write:packages`, `delete:packages`
7. Click "Generate"
8. Copy token immediately (you won't see it again)
9. Paste into GitHub Secret

**Example:**
```
DOCKERHUB_TOKEN = dckr_pat_abcdefg1234567890ABCDEFG
```

### SAFE_API_KEY (Optional)
**Value:** Your Safe trial API key from teosegypt.com
**Format:** `sk-your-actual-key`
**When to add:** When you receive trial key from email

---

## 📋 How to Add Secrets in GitHub

### Method 1: Web UI (Easiest)

1. Go to your repository: https://github.com/Elmahrosa/safe-ingestion-engine
2. Click **Settings** (top right)
3. Left sidebar: **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. **Name:** `DOCKERHUB_USERNAME`
6. **Value:** (paste your Docker Hub username)
7. Click **Add secret**
8. Repeat for `DOCKERHUB_TOKEN`
9. (Optional) Repeat for `SAFE_API_KEY`

### Method 2: GitHub CLI

```bash
# Install GitHub CLI if not already installed
# https://cli.github.com/

# Add Docker Hub username
gh secret set DOCKERHUB_USERNAME --body "yourusername"

# Add Docker Hub access token
gh secret set DOCKERHUB_TOKEN --body "dckr_pat_..."

# Add Safe API key (optional)
gh secret set SAFE_API_KEY --body "sk-..."
```

---

## ✅ Verify Secrets Are Set

```bash
# List all secrets (shows names only, not values)
gh secret list --repo Elmahrosa/safe-ingestion-engine

# Expected output:
# DOCKERHUB_TOKEN       Updated 2024-01-15
# DOCKERHUB_USERNAME    Updated 2024-01-15
# SAFE_API_KEY          Updated 2024-01-15
```

---

## 🆘 Troubleshooting Secrets

### Secret not being recognized

**Problem:** Workflow shows `The following secrets are undefined: DOCKERHUB_USERNAME`

**Solution:**
1. Verify you added the secret to the **correct repository** (not organization)
2. Verify **exact spelling** (case-sensitive): `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`
3. Wait 30 seconds after adding for GitHub to sync
4. Try refreshing the Actions tab

### Push to Docker Hub fails with auth error

**Problem:** `ERROR: denied: requested access to the resource is denied`

**Solution:**
1. Verify `DOCKERHUB_USERNAME` is your Docker Hub username, NOT your email
2. Verify `DOCKERHUB_TOKEN` is your **access token**, NOT your account password
3. Verify token has correct permissions: `read:packages`, `write:packages`, `delete:packages`
4. Test token locally: `docker login -u yourusername` (paste token when prompted)
5. If token doesn't work locally, regenerate it in Docker Hub

### How to regenerate Docker Hub token

1. Go to https://hub.docker.com/ → Profile → Account Settings → Security
2. Find your `github-actions` token
3. Click the 3-dot menu → Delete
4. Click "New Access Token"
5. Name: `github-actions`
6. Permissions: `read:packages`, `write:packages`, `delete:packages`
7. Generate and copy
8. Update GitHub Secret `DOCKERHUB_TOKEN` with new token

---

## 🔒 Security Best Practices

1. **Never commit secrets to git**
   - All secrets are encrypted on GitHub
   - Use `.gitignore` for local `.env` files

2. **Use access tokens, not passwords**
   - Tokens are time-limited
   - Tokens can be revoked instantly
   - Tokens have specific permissions (scope)

3. **Rotate tokens regularly**
   - Generate new token every 90 days
   - Update GitHub Secret
   - Delete old token

4. **Check exposed token history**
   - If token is accidentally committed, it shows in git history
   - Immediately delete token in Docker Hub
   - Generate new one

5. **Use least-privilege permissions**
   - Only grant permissions workflow actually needs
   - For publishing: `write:packages` + `delete:packages`
   - Not `admin:repo_hook` or other broad scopes

---

## 📞 Additional Resources

- GitHub Secrets Docs: https://docs.github.com/en/actions/security-guides/encrypted-secrets
- Docker Hub Access Tokens: https://docs.docker.com/security/for-developers/access-tokens/
- GitHub CLI: https://cli.github.com/

---

## 🧪 Test Secret Configuration

After adding secrets, the next push to main will trigger the workflow.

Monitor progress:
1. Go to **Actions** tab
2. Click **Docker CI/CD Pipeline** (latest run)
3. Expand **Build & Publish to Docker Hub** job
4. Check "Log in to Docker Hub" step

Expected output:
```
[docker] ✓ Logged in to docker.io as yourusername
```

If this fails:
- Check secret spelling (case-sensitive)
- Verify token permissions include `write:packages`
- Test token locally: `docker login -u yourusername`
- Regenerate token in Docker Hub
- Update GitHub Secret

---

## ✨ What Happens After Secrets Are Added

1. First push to `main` triggers workflow
2. All checks run (lint, test, build, security)
3. If all pass, image is built and pushed to Docker Hub
4. Image is tagged with: `latest`, `main`, `<commit-sha>`
5. Docker Hub description is updated

Check Docker Hub:
```bash
docker pull yourusername/safe-ingestion-engine:latest
```

---

## 📋 Checklist Before First Push

- [ ] `DOCKERHUB_USERNAME` secret added
- [ ] `DOCKERHUB_TOKEN` secret added (with write:packages permission)
- [ ] Verified secrets show in GitHub Settings
- [ ] `.github/workflows/docker-ci.yml` file committed locally
- [ ] Ready to push to main branch

---

**Next:** Add these secrets to GitHub, then commit and push the workflow file to trigger the pipeline!
