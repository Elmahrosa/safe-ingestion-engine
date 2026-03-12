# API

## GET /health
Returns `{"status":"ok"}`.

## POST /v1/ingest
Queue an ingestion job.

Headers:
- `X-API-Key`

Body:
```json
{"url":"https://example.com"}
```

## GET /v1/jobs/{job_id}
Return the current status and available excerpt for a queued job.
