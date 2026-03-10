"""
collectors/scraper.py — SSRF-safe, rate-limited HTTP fetcher.
Fixes:
  - fetch_with_metrics() was called in tasks.py but never defined
  - Constructor required positional `guard` arg → removed
  - No URL validation → SSRF attacks possible → added _validate_url()
  - No response-size cap → memory exhaustion → streaming with MAX_RESPONSE_BYTES
"""

import ipaddress
import os
import socket
import time
from typing import Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

MAX_RESPONSE_BYTES = int(os.getenv("MAX_RESPONSE_BYTES", str(5 * 1024 * 1024)))  # 5 MB
FETCH_TIMEOUT_SECS = int(os.getenv("FETCH_TIMEOUT_SECONDS", "10"))

# Private / reserved IP ranges that must be blocked (SSRF protection)
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),   # link-local / AWS metadata
    ipaddress.ip_network("100.64.0.0/10"),    # carrier-grade NAT
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 ULA
]


class SSRFBlockedError(ValueError):
    pass


class SafeScraper:
    """
    HTTP fetcher with SSRF protection, response-size cap, and latency metrics.
    """

    def __init__(self, user_agent: str = "SafeSaaS/1.0"):
        self.user_agent = user_agent
        self._session = self._build_session()

    # ── Session / retry setup ─────────────────────────────────────────────────

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({"User-Agent": self.user_agent})
        return session

    # ── SSRF guard ────────────────────────────────────────────────────────────

    def _validate_url(self, url: str) -> None:
        """
        Reject URLs that resolve to private/internal IP ranges.
        Raises SSRFBlockedError if blocked.
        """
        parsed = urlparse(url)
        hostname = parsed.hostname

        if not hostname:
            raise ValueError(f"Invalid URL (no hostname): {url!r}")
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Only http/https schemes are allowed, got: {parsed.scheme!r}")

        try:
            resolved_ips = socket.gethostbyname_ex(hostname)[2]
        except socket.gaierror as exc:
            raise ValueError(f"DNS resolution failed for {hostname!r}: {exc}") from exc
        for resolved_ip in resolved_ips:
            addr = ipaddress.ip_address(resolved_ip)
            for network in _BLOCKED_NETWORKS:
                if addr in network:
                    raise SSRFBlockedError(
                        f"Blocked: {hostname!r} resolves to private IP {resolved_ip} ({network})")

    # ── Core fetch ────────────────────────────────────────────────────────────

    def fetch_with_metrics(
        self,
        url: str,
        timeout: Optional[int] = None,
    ) -> dict:
        """
        Fetch *url* safely and return a metrics dict:
        {
            success: bool,
            content: str,          # decoded text
            bytes: int,
            latency_ms: int,
            error: str | None,
        }
        """
        t_start = time.monotonic()

        try:
            self._validate_url(url)
        except (ValueError, SSRFBlockedError) as exc:
            return {"success": False, "error": str(exc), "content": "", "bytes": 0, "latency_ms": 0}

        effective_timeout = timeout or FETCH_TIMEOUT_SECS

        try:
            resp = self._session.get(
                url,
                timeout=effective_timeout,
                stream=True,                   # streaming to enforce size cap
                allow_redirects=True,
            )
            resp.raise_for_status()

            # Streaming read with byte cap
            chunks = []
            total_bytes = 0
            for chunk in resp.iter_content(chunk_size=65_536):
                total_bytes += len(chunk)
                if total_bytes > MAX_RESPONSE_BYTES:
                    resp.close()
                    break
                chunks.append(chunk)

            raw_bytes = b"".join(chunks)
            encoding   = resp.encoding or "utf-8"
            content    = raw_bytes.decode(encoding, errors="replace")
            latency_ms = int((time.monotonic() - t_start) * 1000)

            return {
                "success":    True,
                "content":    content,
                "bytes":      len(raw_bytes),
                "latency_ms": latency_ms,
                "error":      None,
            }

        except requests.exceptions.Timeout:
            latency_ms = int((time.monotonic() - t_start) * 1000)
            return {
                "success": False,
                "error": f"Request timed out after {effective_timeout}s",
                "content": "", "bytes": 0, "latency_ms": latency_ms,
            }
        except requests.exceptions.RequestException as exc:
            latency_ms = int((time.monotonic() - t_start) * 1000)
            return {
                "success": False,
                "error": str(exc),
                "content": "", "bytes": 0, "latency_ms": latency_ms,
            }

    # ── Convenience alias ─────────────────────────────────────────────────────

    def fetch(self, url: str, timeout: Optional[int] = None) -> str:
        """Simple fetch — returns decoded content or raises on failure."""
        result = self.fetch_with_metrics(url, timeout=timeout)
        if not result["success"]:
            raise RuntimeError(result["error"])
        return result["content"]
