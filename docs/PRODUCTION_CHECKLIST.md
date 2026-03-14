# Production Checklist — Safe Ingestion Engine

Work through every item before going live. Check each box once confirmed.

---

## 1. Secrets & Environment

- [ ] `.env` file exists on the server and is **not** committed to git
- [ ] `PII_SALT` — set to a random 32-char hex string
- [ ] `API_KEY_SALT` — set to a different random 32-char hex string
- [ ] `GAS_WEBHOOK_SECRET` — set and matches the value in Google Apps Script
- [ ] `REDIS_URL` — points to your actual Redis instance (not localhost if Redis is remote)
- [ ] `USE_REDIS_AUTH=true` — confirm you are using Redis-backed auth, not static list
- [ ] `API_KEY_HASHES_JSON=[]` — empty list (Redis mode doesn't use this)
- [ ] No real secrets in any committed file (`git grep -i password`, `git grep -i secret`)
- [ ] Script properties in Google Apps Script updated with `GAS_WEBHOOK_SECRET`

Generate salts with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 2. Git Repository

- [ ] `git status` shows `nothing to commit, working tree clean`
- [ ] `.env` is listed in `.gitignore` and **not** tracked (`git ls-files .env` returns nothing)
- [ ] No `__pycache__/`, `*.pyc`, or `*.pyo` files tracked
- [ ] Only one app entrypoint: `api/server.py` (no stale `api/main.py`)
- [ ] `VERSION` file is up to date
- [ ] `CHANGELOG.md` updated if there were breaking changes

---

## 3. Dependencies

- [ ] `requirements.txt` is up to date (`pip freeze > requirements.txt` in `.venv`)
- [ ] No known vulnerabilities (`pip-audit`)
- [ ] No high-severity security issues (`bandit -r .`)
- [ ] All imports resolve without errors (`python -c "import api.server"`)

---

## 4. Redis

- [ ] Redis is running and reachable from the API container
- [ ] Redis has a password set in production (`requirepass` in redis.conf)
- [ ] `REDIS_URL` includes the password: `redis://:PASSWORD@host:6379/0`
- [ ] Redis persistence enabled (`appendonly yes` or RDB snapshots)
- [ ] Redis is not exposed on a public port (bind to internal network only)

---

## 5. API Server

- [ ] App starts without errors:
  ```bash
  python -m uvicorn api.server:app --host 0.0.0.0 --port 8000
  ```
- [ ] `/health` returns `{"status": "ok"}`
- [ ] `/docs` loads the Swagger UI
- [ ] `/metrics` returns Prometheus-format text
- [ ] `POST /v1/ingest` returns 401 with no key, 200 with valid key
- [ ] `GET /v1/jobs/{job_id}` returns job status correctly
- [ ] Smoke test passes:
  ```bash
  ./scripts/smoke_test.sh https://safe.teosegypt.com
  ```

---

## 6. Docker & Compose

- [ ] `docker compose build` completes without errors
- [ ] `docker compose up -d` starts all services (redis, api, worker)
- [ ] Redis healthcheck passes before API starts
- [ ] API healthcheck passes before worker starts
- [ ] Logs show no errors: `docker compose logs --tail=50`

---

## 7. Google Apps Script (Billing Bridge)

- [ ] Apps Script deployed as Web App → Execute as Me → Anyone
- [ ] `GAS_WEBHOOK_URL` in `.env` points to the deployed Apps Script URL
- [ ] `GAS_WEBHOOK_SECRET` matches on both sides
- [ ] Test: trigger a paid plan signup → confirm key appears in Redis:
  ```bash
  python scripts/rotate_api_keys.py --list
  ```
- [ ] Test: confirm email arrives with API key after payment

---

## 8. Hostinger / Static Frontend

- [ ] `index.html` deployed to `public_html/index.html`
- [ ] `portal.html` deployed to `public_html/portal.html`
- [ ] `founder.html` deployed to `public_html/founder.html`
- [ ] `docs.html` deployed to `public_html/docs.html`
- [ ] `files/index.html` deployed to `public_html/files/index.html`
- [ ] `API_URL` constant in each HTML file points to `https://safe.teosegypt.com`
- [ ] Founder dashboard password hash updated if password was changed

---

## 9. DNS & TLS

- [ ] `safe.teosegypt.com` resolves to the VPS IP
- [ ] HTTPS certificate issued (Let's Encrypt via Certbot or Caddy)
- [ ] HTTP → HTTPS redirect in place
- [ ] CORS origin in `api/server.py` matches the live frontend domain

---

## 10. Final Sign-off

- [ ] All smoke tests pass against production URL
- [ ] Founder dashboard loads and shows correct data
- [ ] A real trial signup works end-to-end (signup → email → API key → ingest)
- [ ] A real paid signup works end-to-end (payment → webhook → email → key in Redis)
- [ ] Monitoring / uptime alert configured (UptimeRobot, BetterStack, etc.)
