
# API Reference

All protected endpoints require an API key.

Header:

```

X-API-Key: YOUR_KEY

````

---

## POST /v1/ingest_async

Submit a new ingestion job.

### Request

```json
{
 "url": "https://example.com",
 "scrub_pii": true
}
````

### Response

```json
{
 "job_id": "abc123",
 "status": "queued"
}
```

---

## GET /v1/jobs/{job_id}

Retrieve job status.

### Response

```json
{
 "job_id": "abc123",
 "status": "complete",
 "content": "...",
 "pii_redacted": 2
}
```

---

## GET /health

Health check endpoint.

```json
{
 "status": "ok"
}
```

---

## Status Codes

| Status   | Meaning               |
| -------- | --------------------- |
| queued   | waiting for worker    |
| running  | ingestion in progress |
| complete | job finished          |
| failed   | ingestion error       |
| blocked  | policy blocked        |

````

---
