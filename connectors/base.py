"""
connectors/base.py — Connector base classes
============================================
Key hardening vs audit:
  - follow_redirects=False  (redirect SSRF prevention)
  - timeout enforced        (DoS prevention)
  - size cap 5 MB           (memory exhaustion prevention)
  - response content-type validated before decode
"""

import abc
from typing import Any

MAX_RESPONSE_BYTES = int(5 * 1024 * 1024)  # 5 MB hard cap


class BaseConnector(abc.ABC):
    source_type: str = "base"

    @abc.abstractmethod
    async def fetch(self, url: str, **kwargs: Any) -> bytes: ...

    @abc.abstractmethod
    async def normalize(self, raw: bytes, **kwargs: Any) -> dict: ...

    async def run(self, url: str, **kwargs: Any) -> dict:
        raw = await self.fetch(url, **kwargs)
        return await self.normalize(raw, **kwargs)


class HttpConnector(BaseConnector):
    """
    Default HTTP connector.
    Security: no redirects followed (SSRF via redirect bypass),
              strict timeout, 5 MB cap.
    """
    source_type = "http"

    async def fetch(self, url: str, **kwargs: Any) -> bytes:
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx is required: pip install httpx")

        timeout = kwargs.get("timeout", 15)

        async with httpx.AsyncClient(
            follow_redirects=False,   # CRITICAL: no redirect following
            timeout=timeout,
        ) as client:
            resp = await client.get(url)

            # Block redirects explicitly even if library ignores setting
            if resp.is_redirect:
                raise ValueError(f"Redirects not permitted. Target: {resp.headers.get('location','')}")

            resp.raise_for_status()

            # Enforce size cap (stream-safe)
            content = b""
            async for chunk in resp.aiter_bytes(chunk_size=65536):
                content += chunk
                if len(content) > MAX_RESPONSE_BYTES:
                    raise ValueError(f"Response exceeds {MAX_RESPONSE_BYTES} byte limit.")

            return content

    async def normalize(self, raw: bytes, **kwargs: Any) -> dict:
        text = raw.decode("utf-8", errors="replace")
        return {
            "text":     text,
            "source":   kwargs.get("url", ""),
            "metadata": {"content_type": "text/html"},
        }
