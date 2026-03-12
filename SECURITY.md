# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | ✅ Active security updates |
| 0.x     | ❌ End of life |

## Reporting Vulnerabilities

**Do not open public GitHub issues for security vulnerabilities.**

Email: **security@teosegypt.com**

Include in your report:
- Description of the vulnerability
- Steps to reproduce
- Affected component and version
- Potential impact assessment
- Suggested fix (optional)

We will acknowledge within **48 hours** and target a fix within **7 days** for critical issues.

---

## Security Architecture

### Authentication
- API keys stored as **SHA-256 hashes** — never plaintext
- Keys are never logged or returned in API responses
- Format: `sk-safe-XXXXXXXXXX` (delivered by email on signup)

### Authorization
- **IDOR protection**: `GET /jobs/{id}` validates `job.user_id == authenticated_user.id`. Non-owned jobs return 404 (not 403, to prevent enumeration).
- **Atomic credit deduction**: `UPDATE users SET credits=credits-1 WHERE id=? AND credits>0` — prevents TOCTOU race condition.

### SSRF Protection
All URLs are validated before any network call. The following are blocked at the IP layer (post-DNS resolution):

| Range | Description |
|---|---|
| 10.0.0.0/8 | Private network |
| 172.16.0.0/12 | Private network |
| 192.168.0.0/16 | Private network |
| 127.0.0.0/8 | Loopback |
| 169.254.0.0/16 | Link-local / AWS metadata endpoint |
| 100.64.0.0/10 | Carrier-grade NAT |
| ::1/128 | IPv6 loopback |
| fc00::/7 | IPv6 ULA |
| fe80::/10 | IPv6 link-local |

DNS resolution happens first; all resolved IPs are checked — protecting against DNS rebinding attacks.

### PII Scrubbing
- Runs **in-memory** before any data is written to storage
- Unicode normalization (NFKC) applied before regex matching — prevents obfuscation bypass
- Patterns: email, phone (NA + international), SSN, IPv4, credit card (Visa, Mastercard, Amex, Discover, Diners, JCB)
- Optional: Microsoft Presidio NER for higher accuracy

### Rate Limiting
- **5 requests/minute per IP** on `POST /v1/ingest_async` (via slowapi)
- **10 concurrent jobs per API key** enforced at worker level
- **100 URLs/day per domain** enforced by PolicyEngine crawl budget

### Response Safety
- **5 MB streaming cap** per fetch — prevents memory exhaustion
- **10 second timeout** (configurable, max 30s)
- Redirect chain validated hop-by-hop

### Infrastructure
- **robots.txt**: checked before every fetch, fails open on network error (logged)
- **Dashboard admin**: password-protected via `DASHBOARD_ADMIN_PASSWORD` env var
- **Docker**: services run with health checks; worker waits for Redis to be healthy

### CI/CD Security Pipeline
Every push to `main` runs:
- **Bandit** — Python static security analysis
- **Trivy** — container and filesystem vulnerability scanning
- **pip-audit** — dependency CVE audit

---

## Known Limitations

- **Phone number detection** covers NA and common international formats. Unusual regional formats may not be caught by the regex fallback. Use Presidio (optional) for broader coverage.
- **SQLite in production**: SQLite is sufficient for low-to-medium volume. For high concurrency or multi-instance deployments, migrate to PostgreSQL (see `DATABASE_URL` in `.env.example`).
- **robots.txt crawl delay**: The engine respects `Disallow` rules but does not implement `Crawl-delay` directive timing. Rate limiting is applied via YAML crawl budgets instead.

---

## Hall of Fame

Responsible disclosures acknowledged here (with researcher's permission).

*None yet — be the first.*

---

*Last reviewed: March 2026 · Maintained by Ayman Seif, Elmahrosa International*
