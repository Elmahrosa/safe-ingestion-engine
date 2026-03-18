# Replace _get_client() and fetch() with these versions:

async def _get_client(self) -> httpx.AsyncClient:
    """Create client WITHOUT follow_redirects — control per-request instead."""
    if self._client is None or self._client.is_closed:
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=False,  # ✅ Always False at client level (defensive default)
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
    return self._client

async def fetch(self, url: str, *, follow_redirects: bool = False, **kwargs) -> FetchResult:
    """
    Fetch with per-call redirect control.
    
    Args:
        url: Target URL
        follow_redirects: Whether to follow HTTP redirects (default: False)
        **kwargs: Extra httpx.request kwargs
    """
    await self.validate_source(url)
    client = await self._get_client()
    
    # ✅ Pass follow_redirects at request level — overrides client default
    async with client.stream(
        "GET", 
        url, 
        headers={"User-Agent": "safe-ingestion-engine/2.0"},
        follow_redirects=follow_redirects,  # ✅ Per-call control
        **kwargs
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
