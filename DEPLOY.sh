#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# AI INGESTION GATEWAY — Full Deploy Checklist
# Run these commands IN ORDER on your VPS or local machine
# ═══════════════════════════════════════════════════════════

# ── STEP 1: Move the new files into correct locations ────────
# The files were committed to root by mistake.
# These commands move them to where the app expects them.

git mv auth.py core/auth.py
git mv pii.py core/pii.py
git mv ingest.py api/routes/ingest.py

# Commit the moves
git commit -m "fix: move auth/pii/ingest to correct directories"
git push


# ── STEP 2: Fix the broken test ─────────────────────────────
# The old test expected skip-on-large-input.
# New pii.py truncates instead of skipping — test must match.
# Copy test_pii_regex.py from the files we gave you, then:

git add tests/security/test_pii_regex.py
git commit -m "test: update large-input pii test for truncation behavior"
git push


# ── STEP 3: Make repo private ───────────────────────────────
# GitHub → your repo → Settings → scroll to Danger Zone
# → Change repository visibility → Private
# Do this BEFORE deploying to VPS.


# ── STEP 4: Remove .env from git history ────────────────────
git rm --cached .env 2>/dev/null || true
echo ".env" >> .gitignore
git add .gitignore
git commit -m "fix: remove .env from tracking"
git push


# ── STEP 5: Set up .env on your VPS ─────────────────────────
# SSH into your VPS then:
# nano .env
# Paste the .env file we gave you, fill in the 3 secrets and password.
# Generate secrets with:
#   python -c "import secrets; print(secrets.token_hex(32))"
# Run that command 3 times for PII_SALT, API_KEY_SALT, GAS_WEBHOOK_SECRET.


# ── STEP 6: Deploy with Docker ───────────────────────────────
# On your VPS:
git pull
docker compose down
docker compose up --build -d

# Verify it's running:
curl https://safe.teosegypt.com/health
# Expected: {"status": "ok", "version": "2.0.0"}


# ── STEP 7: Run smoke test ───────────────────────────────────
# On your VPS (with GAS_WEBHOOK_SECRET exported):
export GAS_WEBHOOK_SECRET=your-value-here
bash scripts/smoke_test.sh https://safe.teosegypt.com
# All checks should pass with ✓


# ── STEP 8: Restrict /metrics endpoint ──────────────────────
# Add this to your Nginx config inside the server block:
#
#   location /metrics {
#       allow 127.0.0.1;
#       deny all;
#   }
#
# Then: nginx -t && systemctl reload nginx


# ── STEP 9: Set up GAS Script Properties ────────────────────
# In Google Apps Script → Project Settings → Script Properties:
#
#   GAS_WEBHOOK_SECRET = same value as in your .env
#   VPS_BASE_URL       = https://safe.teosegypt.com
#   SHEET_ID           = your Google Sheet ID
#   ADMIN_EMAIL        = ayman@teosegypt.com
#
# Then deploy GAS as Web App (Execute as: Me, Access: Anyone)
# Copy the Web App URL — this is your signup webhook endpoint.


# ── STEP 10: Test the full signup flow ──────────────────────
# In GAS editor, run testSignup() — check Logger output.
# You should see a new row in your Google Sheet.
# Check your email for the welcome message with API key.
# Use the API key to call: curl https://safe.teosegypt.com/v1/account -H "X-API-Key: aig_..."


# ── STEP 11: Wire up the signup form on safe.teosegypt.com ──
# Your signup form should POST to the GAS Web App URL:
#
# fetch("https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec", {
#   method: "POST",
#   headers: { "Content-Type": "application/json" },
#   body: JSON.stringify({
#     email: formEmail,
#     plan: "trial",
#     secret: "YOUR_GAS_WEBHOOK_SECRET"   // same as in .env
#   })
# })
#
# On success: show "Check your email for your API key."
# NOTE: never expose GAS_WEBHOOK_SECRET in frontend JS.
# Instead: have your VPS proxy the signup request server-side,
# OR create a separate lightweight Flask/Express endpoint that
# adds the secret before forwarding to GAS.


# ── WHAT EACH .env VALUE IS AND WHERE IT GOES ────────────────
#
# PII_SALT
#   → generate: python -c "import secrets; print(secrets.token_hex(32))"
#   → add to: .env on VPS
#   → used by: core/pii.py to HMAC-hash PII tokens
#
# API_KEY_SALT
#   → generate: python -c "import secrets; print(secrets.token_hex(32))"
#   → add to: .env on VPS
#   → used by: core/auth.py to HMAC-hash API keys before Redis storage
#
# GAS_WEBHOOK_SECRET
#   → generate: python -c "import secrets; print(secrets.token_hex(32))"
#   → add to: .env on VPS  AND  GAS Script Properties
#   → used by: /internal/provision, /internal/expire to authenticate GAS calls
#
# DASHBOARD_ADMIN_PASSWORD
#   → choose any strong password (min 12 chars)
#   → add to: .env on VPS
#   → used by: Streamlit dashboard admin tab
#
# DATABASE_URL
#   → get from: Railway.app → PostgreSQL → connection string
#   → add to: .env on VPS
#
# REDIS_URL / CELERY_BROKER_URL / CELERY_RESULT_BACKEND
#   → if using Docker Compose: redis://redis:6379/0,1,2 (no change needed)
#   → if using Railway Redis: get URL from Railway dashboard
#   → add to: .env on VPS
#
# CORS_ORIGINS_JSON
#   → your frontend domain exactly as in browser URL bar
#   → format: ["https://safe.teosegypt.com"]
#   → add to: .env on VPS
