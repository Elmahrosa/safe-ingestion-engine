
# Safe Ingestion Engine

> **Compliance-first web data ingestion API for AI agents and developers.**
> PII auto-redacted. robots.txt enforced. SSRF blocked. Every request logged immutably.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Status: Live](https://img.shields.io/badge/Status-Live-green.svg)](https://safe.teosegypt.com)
[![x402: Enabled](https://img.shields.io/badge/x402-USDC%20on%20Base-blue.svg)](https://x402.org)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)

---

## The Problem

In 2026, scraped web data is a **legal liability** until proven clean.

- EU AI Act enters full enforcement August 2026
- 70+ copyright lawsuits filed against AI companies for scraping
- robots.txt moving toward legal enforceability
- GDPR fines for PII in AI training data are real and increasing

**Your AI agent fetching raw web data is accumulating compliance risk with every request.**

---

## One-Line Integration

    curl -X POST https://safe.teosegypt.com/v1/ingest_async \
      -H "X-API-Key: sk-your-key" \
      -H "Content-Type: application/json" \
      -d '{"url": "https://example.com/page"}'

Response: {"job_id": "3f8c2b1a-...", "status": "queued"}

    curl https://safe.teosegypt.com/v1/jobs/3f8c2b1a-... \
      -H "X-API-Key: sk-your-key"

Response: {"status": "completed", "pii_found": 3, "result_excerpt": "...clean HTML..."}

---

## Compliance Features

| Feature | Status |
|---|---|
| PII Scrubber — email, phone, SSN, IPv4, credit card | Active |
| SSRF Guard — async DNS blocks private/loopback/reserved IPs | Active |
| robots.txt Enforcement — checked on every request | Active |
| Crawl Budget — per-domain rate limiting via Redis | Active |
| Immutable Audit Log — job ID, URL, PII count, key hash | Active |
| Circuit Breaker — pybreaker on HTTP connector | Active |
| Idempotency Keys — safe agent retries, no double billing | Active |
| 5 MB Cap — streaming fetch with hard size guard | Active |
| HMAC Key Hashing — keys never stored in plaintext | Active |
| Atomic Credit Deduction — Redis WATCH/MULTI/EXEC | Active |

---

## Architecture

    POST /v1/ingest_async
            |
            v
    [ Auth Layer ]       HMAC key validation + credit check (Redis)
            |
            v
    [ Policy Engine ]    robots.txt + crawl budget — blocked = 0 credits
            |
            v
    [ SSRF Guard ]       Async DNS — blocks private/loopback/reserved IPs
            |
            v
    [ Safe Fetch ]       httpx + circuit breaker + 5 MB cap
            |
            v
    [ PII Scrubber ]     Regex — HMAC-hashed redaction tokens
            |
            v
    [ Audit Log ]        job_id, url, pii_count, key_hash written to DB
            |
            v
      Clean content + job_id returned to caller

---

## API Reference

### POST /v1/ingest_async

Headers: X-API-Key: sk-...

Body: {"url": "https://example.com/page", "idempotency_key": "optional-uuid"}

Response: {"job_id": "...", "status": "queued"}

### GET /v1/jobs/{job_id}

Status flow: queued -> running -> completed | failed

Response: {"job_id": "...", "status": "completed", "pii_found": 3, "result_excerpt": "..."}

### GET /v1/account

Response: {"valid": true, "credits": 97, "plan": "starter"}

### GET /health and GET /metrics

Health check and Prometheus metrics.

---

## Pricing

| Plan | Credits | Price | Per URL |
|------|---------|-------|---------|
| Trial | 5 | Free | - |
| Starter | 100 | $5 USDC | $0.05/URL |
| Growth | 1,000 | $20 USDC | $0.02/URL |
| Enterprise | 50,000 | $500 USDC | $0.01/URL |

Payment: USDC on Base. Wallet: 0xd9CA11Dde3810a1BA9B5E1a4b6b76F5a419FAb41

Blocked requests cost 0 credits.

See docs/X402_INTEGRATION.md for x402 agent payments — no account required.

---

## Quick Start

### Hosted API

Get a key at https://safe.teosegypt.com and start immediately.

### Self-hosted

    git clone https://github.com/Elmahrosa/safe-ingestion-engine
    cd safe-ingestion-engine
    cp .env.example .env
    python -c "import secrets; print(secrets.token_hex(32))"
    docker compose up --build

---

## AI Agent Integration (Python)

    import asyncio, httpx

    async def safe_fetch(url, api_key):
        async with httpx.AsyncClient(
            base_url="https://safe.teosegypt.com",
            headers={"X-API-Key": api_key},
            timeout=30.0,
        ) as client:
            r = await client.post("/v1/ingest_async", json={"url": url})
            job_id = r.json()["job_id"]
            for _ in range(30):
                await asyncio.sleep(2)
                result = await client.get(f"/v1/jobs/{job_id}")
                if result.json()["status"] in ("completed", "failed"):
                    return result.json()

## MCP Integration (Claude / Cursor / Windsurf)

    {
      "mcpServers": {
        "safe-ingestion": {
          "command": "python",
          "args": ["mcp_server.py"],
          "env": {
            "SAFE_API_KEY": "sk-your-key",
            "SAFE_API_BASE": "https://safe.teosegypt.com"
          }
        }
      }
    }

See docs/AI_AGENT_INTEGRATION.md for LangChain, CrewAI, and full async patterns.

---

## Part of the TeosMCP Agent Safety Stack

| Layer | Tool | Protects |
|-------|------|---------|
| Data In | Safe Ingestion Engine (this repo) | Clean web data — PII scrubbed, SSRF blocked |
| Code Out | CodeGuard MCP github.com/Elmahrosa/agent-code-risk-mcp | Code risk scored before execution |
| On-Chain | TeosLinker github.com/Elmahrosa/teoslinker-bot | Transaction monitoring + execution guard |

---

## Requirements

Python 3.11+ | Redis 7+ | Docker + Compose | Optional: PostgreSQL

---

## Security / License / Contact

- Security: SECURITY.md
- License: MIT
- Live API: https://safe.teosegypt.com
- Enterprise: ayman@teosegypt.com
- Built by Elmahrosa International — Cairo, Egypt
