# Changelog

All notable changes are documented here.  
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

---

## [1.0.1] — 2026-03-12

### Security (Post-Launch Audit Fixes)

| # | File | Finding | Fix |
|---|---|---|---|
| A | `api/server.py` | Job IDs were short hex strings → enumerable (IDOR, CVSS 7.1) | Replaced with full `uuid.uuid4()` (32 chars, 122 bits entropy) |
| B | `api/server.py` | `GET /jobs/{id}` had no ownership check → any authenticated user could poll any job | Added `if row[0] != user["id"]: raise 404` |
| C | `api/server.py` | No IP-based rate limiting on ingest endpoint | Added `slowapi` 5/min per IP |
| D | `collectors/scraper.py` | SSRF blocklist incomplete — missing carrier-grade NAT, benchmarking, IETF ranges, IPv6 ULA/link-local | Extended `_BLOCKED_NETWORKS` to full RFC1918 + RFC6890 + IPv6 |
| E | `core/pii.py` | PII regex bypassable via unicode obfuscation (e.g. `\u0040` for `@`) | Added `unicodedata.normalize("NFKC")` before all pattern matching |
| F | `core/pii.py` | Phone regex: NA-only format, missed international numbers | Extended pattern to match `+XX` international prefix format |
| G | `requirements.txt` | No version pins → non-reproducible builds, supply chain risk | All dependencies pinned to exact versions |

---

## [1.0.0] — 2026-03-11

### Added
- Safe ingestion pipeline (FastAPI + Celery + Redis)
- PolicyEngine: YAML rules + robots.txt + crawl budget enforcement
- SafeScraper: SSRF protection, response size cap, retry logic
- PIIScrubber: email, phone, SSN, IPv4, credit card — redact or hash modes
- Full audit log with PDF export (ReportLab)
- Streamlit monitoring dashboard with metrics tab
- USDC micropayment integration (Base network)
- Pay-as-you-go pricing ($0.15/URL, no expiry)
- Docker Compose deployment with healthchecks

### Security (Pre-Launch Audit — 20 Bugs Fixed)

#### Critical
| # | File | Bug | Fix |
|---|---|---|---|
| 1 | `core/database.py` | `log_audit`, `log_metrics`, `insert_raw` imported everywhere but never defined | Added all three functions |
| 2 | `collectors/scraper.py` | `fetch_with_metrics()` called in tasks.py but never defined | Implemented method |
| 3 | `collectors/scraper.py` | Constructor required positional `guard` arg; callers passed only `user_agent` → TypeError | Removed unused `guard` param |
| 4 | `core/policy.py` | `policy.evaluate()` called everywhere; only `decide()` existed → AttributeError | Added `evaluate()` as canonical method |
| 5 | `api.py` | API keys stored and compared in plaintext SQLite | SHA-256 hash before storage and lookup |
| 6 | `api/server.py` | Credit deduction had TOCTOU race — two concurrent requests could both pass `credits > 0` | Atomic `UPDATE WHERE credits > 0` + rowcount check |

#### Security
| # | File | Issue | Fix |
|---|---|---|---|
| 7 | `collectors/scraper.py` | No URL validation — SSRF against localhost, 192.168.*, etc. possible | Added `_validate_url()` with `_BLOCKED_NETWORKS` guard |
| 8 | `collectors/scraper.py` | No response size cap | Streaming fetch with `MAX_RESPONSE_BYTES` cap |
| 9 | `core/compliance.py` | Bare `except:` returned BLOCKED on any exception including timeouts | Fail-open with logged warning |
| 10 | `dashboard/app.py` | Admin section showed all user data to anyone | Password-protected via `DASHBOARD_ADMIN_PASSWORD` |
| 11 | `.github/workflows/security.yml` | `actions/checkout@v6` and `setup-python@v6` don't exist | Pinned to `@v4` / `@v5`; added Trivy container scan |

#### Correctness & Quality
| # | File | Issue | Fix |
|---|---|---|---|
| 12 | `api/tasks.py` | DB connection opened but never closed (success path) | `try/finally conn.close()` |
| 13 | `core/pii.py` | PHONE regex too greedy — matched any 8+ digit sequence | Tightened to recognizable NA phone format |
| 14 | `core/pii.py` | Missing SSN, IPv4, credit-card patterns | Added all three |
| 15 | `core/policy.py` | No robots.txt integration despite being the primary policy entry point | Integrated `_check_robots()` |
| 16 | `core/policy.py` | No crawl-budget enforcement at runtime | Added in-memory per-domain counter with daily reset |
| 17 | `dashboard/app.py` | PDF export was a blank page | Now exports actual audit table via ReportLab platypus |
| 18 | `dashboard/app.py` | `request_metrics` table existed but had no dashboard view | Added Metrics tab with KPI cards |
| 19 | `main.py` | `load_dotenv()` called on every import, overriding env vars in Docker | Moved inside `if __name__ == "__main__"` |
| 20 | `docker-compose.yml` | No healthchecks — worker could start before Redis was ready | Added `healthcheck` + `condition: service_healthy` |

---

## [0.9.0] — 2026-03-01

### Initial development release (internal)
- Core pipeline architecture
- Basic FastAPI endpoints
- Celery + Redis integration
- SQLite storage
