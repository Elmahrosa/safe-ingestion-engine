# Security

## Core controls

- SSRF protection blocks private, reserved, loopback, multicast, and link-local IP space
- API keys are validated by SHA-256 hash comparison
- Crawl budgets are enforced in Redis instead of in-process memory
- PII is scrubbed before persistence by deterministic HMAC-based replacement
- robots.txt is enforced with configurable error behavior
- Celery retries use exponential backoff with jitter
- Structured logs are emitted for key security-relevant events

## Current limitations

- SQLite is acceptable for local use and light workloads, but not ideal for heavy production write concurrency
- PII regex coverage is intentionally simple and should be expanded for stricter compliance targets
- DNS validation is still blocking and can be upgraded later to async DNS for higher throughput
