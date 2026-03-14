from __future__ import annotations

import ipaddress
from typing import Optional
from urllib.parse import urlparse

import aiodns
import httpx
from pybreaker import CircuitBreaker

from connectors.base import DataConnector, FetchResult
from core.config import get_settings
from core.logging import logger


class SSRFBlockedError(Exception):
    pass


class HTTPConnector(DataConnector):
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.timeout = httpx.Timeout(settings.request_timeout_seconds, connect=3.0)
        self._client: Optional[httpx.AsyncClient] = None
        self.fetch_breaker = CircuitBreaker(fail_max=3, reset_timeout=60)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=self.settings.allow_redirects,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            )
        return self._client

    async def _validate_host_async(self, url: str) -> None:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            raise SSRFBlockedError("missing hostname")
        if parsed.scheme not in {"http", "https"}:
            raise SSRFBlockedError("unsupported scheme")

        resolver = aiodns.DNSResolver()
        result = await resolver.gethostbyname(hostname, socket_family=0)
        addrs = [r.host for r in result.addresses]

        for raw_ip in addrs:
            ip = ipaddress.ip_address(raw_ip)
            if any([ip.is_private, ip.is_loopback, ip.is_link_local, ip.is_reserved, ip.is_multicast]):
                logger.warning(
                    "ssrf.blocked",
                    url=url,
                    resolved_ip=raw_ip,
                    security_event=True,
                )
                raise SSRFBlockedError(f"blocked address {raw_ip}")

    async def validate_source(self, url: str) -> bool:
        await self._validate_host_async(url)
        return True

    async def _fetch_with_breaker(self, url: str, client: httpx.AsyncClient) -> httpx.Response:
        @self.fetch_breaker
        async def _inner() -> httpx.Response:
            return await client.get(url, headers={"User-Agent": "safe-ingestion-engine/2.0"})

        return await _inner()

    async def fetch(self, url: str, **kwargs) -> FetchResult:
        await self.validate_source(url)
        client = await self._get_client()

        async with client.stream("GET", url, headers={"User-Agent": "safe-ingestion-engine/2.0"}) as response:
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

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def get_capabilities(self) -> dict:
        return {
            "redirects": self.settings.allow_redirects,
            "streaming_size_guard": True,
            "circuit_breaker": True,
            "async_dns_validation": True,
        }
