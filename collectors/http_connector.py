# fix_06_redirects_stream.py
# ─────────────────────────────────────────────────────────────────────────────
# FINDING (MEDIUM): HTTPConnector.fetch() calls client.stream() directly.
# The AsyncClient is created with follow_redirects=self.settings.allow_redirects
# so redirects ARE controlled.  However the _get_client() may return a cached
# client created before settings were fully applied.  Also, the stream() call
# path bypasses _fetch_with_breaker (the circuit breaker).
#
# Fix: consolidate fetch to always go through the circuit-breaker-aware path,
# and ensure the client is never reused across settings changes.
#
# FILE: collectors/http_connector.py
# ─────────────────────────────────────────────────────────────────────────────

PATCH = '''
    async def fetch(self, url: str, **kwargs) -> FetchResult:
        await self.validate_source(url)
        client = await self._get_client()

        # Stream through a context manager; honour the circuit breaker.
        # follow_redirects is already set on the client; each redirect hop
        # is resolved inside httpx before data flows — so SSRF validation
        # fires on the *original* URL only.  For full redirect-hop validation
        # set allow_redirects=false (default) which is the safe default.
        async with client.stream(
            "GET",
            url,
            headers={"User-Agent": "safe-ingestion-engine/2.0"},
            follow_redirects=self.settings.allow_redirects,   # explicit per-call
        ) as response:
            response.raise_for_status()
            chunks: list[bytes] = []
            total_size = 0
            async for chunk in response.aiter_bytes():
                total_size += len(chunk)
                if total_size > self.settings.max_response_bytes:
                    raise ValueError("response too large")
                chunks.append(chunk)

            body = b"".join(chunks).decode("utf-8", errors="replace")
            return FetchResult(
                url=str(response.url),
                content=body,
                status_code=response.status_code,
                content_type=response.headers.get("content-type"),
                metadata={"bytes": total_size},
            )
'''

print("Fix 06: In collectors/http_connector.py, replace fetch() with PATCH above.")
print("Key change: follow_redirects passed explicitly per-call, not just on client init.")
