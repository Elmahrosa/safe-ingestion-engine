# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | ✅ Yes    |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Email: aams1969@gmail.com  
Subject: `[SECURITY] Safe Ingestion Engine — <brief description>`

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact (CVSS estimate if possible)
- Any suggested fix

You will receive a response within **48 hours**.

## Disclosure Policy

- Vulnerabilities are fixed within **7 days** of confirmation for critical/high severity
- A CVE will be requested for CVSS ≥ 7.0 findings
- Credit given to reporters unless anonymity is requested

## Known Mitigations

| Risk | Mitigation |
|------|-----------|
| SSRF | Private IP blocklist + scheme allowlist + shortener blocklist in `core/security.py` |
| Auth brute-force | SlowAPI rate limits on all auth endpoints |
| Job enumeration | UUIDv4 job IDs + key-scoped ownership check |
| Redis RCE | `requirepass` enforced, bound to 127.0.0.1 |
| Celery RCE | JSON serializer only, no pickle |
| Secret timing | `hmac.compare_digest` on all secret comparisons |
| Redirect SSRF | `follow_redirects=False` in HttpConnector |
| Dep CVEs | `pip-audit` in CI on every PR |
