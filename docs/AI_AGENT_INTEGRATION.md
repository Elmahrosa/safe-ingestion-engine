# AI Agent Integration Guide — Safe Ingestion Engine

This guide explains how to integrate Safe Ingestion Engine into an AI agent pipeline — LangChain, LlamaIndex, AutoGen, CrewAI, or any custom agent framework.

---

## Overview

Safe Ingestion Engine exposes a simple REST API that:
1. Accepts a URL
2. Fetches the content, scrubs PII
3. Returns clean, structured text suitable for embedding or RAG

Agents interact with two endpoints:

| Endpoint | Purpose |
|---|---|
| `POST /v1/ingest` | Submit a URL for async ingestion |
| `GET /v1/jobs/{job_id}` | Poll for results |

---

## Authentication

All requests require an `X-API-Key` header:

```
X-API-Key: sk-safe-XXXXXXXXXX
```

Keys are issued after signup at [safe.teosegypt.com](https://safe.teosegypt.com).

---

## Basic Usage (Python)

```python
import httpx
import time

BASE = "https://safe.teosegypt.com"
KEY  = "sk-safe-XXXXXXXXXX"          # your API key

def ingest(url: str, scrub_pii: bool = True) -> dict:
    """Submit a URL and poll until done. Returns the result dict."""
    headers = {"X-API-Key": KEY, "Content-Type": "application/json"}

    # 1. Submit
    r = httpx.post(f"{BASE}/v1/ingest", json={"url": url, "scrub_pii": scrub_pii}, headers=headers)
    r.raise_for_status()
    job_id = r.json()["job_id"]

    # 2. Poll
    for _ in range(30):          # max 30 attempts × 2 s = 60 s timeout
        time.sleep(2)
        r = httpx.get(f"{BASE}/v1/jobs/{job_id}", headers=headers)
        r.raise_for_status()
        data = r.json()
        if data["status"] == "done":
            return data["result"]
        if data["status"] == "failed":
            raise RuntimeError(f"Ingestion failed: {data.get('error')}")

    raise TimeoutError(f"Job {job_id} did not complete within 60 s")
```

---

## LangChain Tool

```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import httpx, time

class IngestInput(BaseModel):
    url: str = Field(description="URL to ingest and scrub")

class SafeIngestionTool(BaseTool):
    name        = "safe_ingestion"
    description = "Fetches a URL, scrubs PII, and returns clean text for RAG."
    args_schema = IngestInput

    api_key: str
    base_url: str = "https://safe.teosegypt.com"

    def _run(self, url: str) -> str:
        headers = {"X-API-Key": self.api_key}
        r = httpx.post(f"{self.base_url}/v1/ingest", json={"url": url}, headers=headers, timeout=10)
        r.raise_for_status()
        job_id = r.json()["job_id"]

        for _ in range(30):
            time.sleep(2)
            r = httpx.get(f"{self.base_url}/v1/jobs/{job_id}", headers=headers, timeout=10)
            data = r.json()
            if data["status"] == "done":
                return data["result"]["text"]
            if data["status"] == "failed":
                return f"Error: {data.get('error')}"

        return "Error: ingestion timed out"

    async def _arun(self, url: str) -> str:
        raise NotImplementedError("Use async httpx for async support")


# Usage in an agent
tool = SafeIngestionTool(api_key="sk-safe-XXXXXXXXXX")
text = tool._run("https://arxiv.org/abs/2401.00001")
```

---

## LlamaIndex Reader

```python
from llama_index.core import Document
from llama_index.core.readers.base import BaseReader
import httpx, time

class SafeIngestionReader(BaseReader):
    def __init__(self, api_key: str, base_url: str = "https://safe.teosegypt.com"):
        self.api_key  = api_key
        self.base_url = base_url

    def load_data(self, urls: list[str]) -> list[Document]:
        docs = []
        for url in urls:
            text = self._ingest(url)
            docs.append(Document(text=text, metadata={"source": url}))
        return docs

    def _ingest(self, url: str) -> str:
        headers = {"X-API-Key": self.api_key}
        r = httpx.post(f"{self.base_url}/v1/ingest", json={"url": url}, headers=headers)
        r.raise_for_status()
        job_id = r.json()["job_id"]
        for _ in range(30):
            time.sleep(2)
            data = httpx.get(f"{self.base_url}/v1/jobs/{job_id}", headers=headers).json()
            if data["status"] == "done":
                return data["result"]["text"]
        return ""
```

---

## Error Reference

| HTTP Code | Meaning | Fix |
|---|---|---|
| `401` | Invalid or expired API key | Check key, re-register via portal |
| `422` | Missing or malformed request body | Include `url` field in JSON body |
| `404` | Job not found (GET /v1/jobs) | Job expired (24 h TTL) — re-submit |
| `429` | Rate limit exceeded | Back off and retry |
| `500` | Server error | Check `/v1/status`, contact support |

---

## Rate Limits

| Plan | Requests / day |
|---|---|
| Trial | 5 |
| Starter | 300 |
| Growth | 900 |
| Yearly Starter | 3 000 |
| Yearly Growth | 9 000 |

---

## PII Scrubbing

When `scrub_pii: true` (default), the engine removes:
- Email addresses
- Phone numbers
- Credit card numbers
- Social security / national ID patterns
- IP addresses
- Physical addresses (best-effort)

Set `scrub_pii: false` only if you have verified consent from data subjects.

---

## Webhook Notifications (optional)

Pass a `webhook_url` in the ingest request to receive a POST callback when the job completes — no polling required:

```json
{
  "url": "https://example.com/article",
  "scrub_pii": true,
  "webhook_url": "https://your-agent-server.com/callback"
}
```

The callback payload will be:
```json
{
  "job_id": "...",
  "status": "done",
  "result": { "text": "...", "metadata": {} }
}
```

---

## Support

- Portal: [safe.teosegypt.com/portal.html](https://safe.teosegypt.com/portal.html)
- Docs: [safe.teosegypt.com/docs.html](https://safe.teosegypt.com/docs.html)
- Email: aams1969@gmail.com
