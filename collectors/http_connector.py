from dataclasses import dataclass
import ipaddress
import socket
from urllib.parse import urlparse

import httpx

from core.config import get_settings
from core.logging import logger


settings = get_settings()


@dataclass
class FetchResult:
    url: str
    content: str
    status_code: int
    content_type: str | None


class SSRFBlockedError(Exception):
    pass


class HTTPConnector:
    def __init__(self):
        self.timeout = httpx.Timeout(settings.request_timeout_seconds, connect=3.0)

    def _validate_host(self, url: str) -> None:
        parsed = urlparse(url)
        hostname = parsed.hostname

        if not hostname:
            raise SSRFBlockedError("missing hostname")
        if parsed.scheme not in {"http", "https"}:
            raise SSRFBlockedError("unsupported scheme")

        _, _, addrs = socket.gethostbyname_ex(hostname)
        for raw_ip in addrs:
            ip = ipaddress.ip_address(raw_ip)
            if any([ip.is_private, ip.is_loopback, ip.is_link_local, ip.is_reserved, ip.is_multicast]):
                logger.warning("ssrf.blocked", url=url, resolved_ip=raw_ip)
                raise SSRFBlockedError(f"blocked address {raw_ip}")

    async def fetch(self, url: str) -> FetchResult:
        self._validate_host(url)

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=settings.allow_redirects,
        ) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "safe-ingestion-engine/2.0"},
            )
            response.raise_for_status()

            body = response.text
            if len(body.encode("utf-8")) > settings.max_response_bytes:
                raise ValueError("response too large")

            return FetchResult(
                url=str(response.url),
                content=body,
                status_code=response.status_code,
                content_type=response.headers.get("content-type"),
            )
