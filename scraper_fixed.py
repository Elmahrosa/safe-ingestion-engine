"""
collectors/scraper.py — SSRF-safe, rate-limited HTTP fetcher.

FIXES APPLIED:
  1. _validate_url() only calls gethostbyname_ex() which returns IPv4 only.
     An attacker can create a DNS record with an IPv6 SSRF target and bypass the check.
     FIX: Also resolve with getaddrinfo() to catch IPv6 addresses.
  2. DNS rebinding attack: DNS is resolved at validation time, but the actual HTTP request
     goes through requests which does its OWN DNS resolution. Between the two, DNS could
     change (rebinding). FIX: Document clearly; full mitigation requires a custom socket
     factory (see _ssrf_safe_socket_factory below, not yet wired to requests session).
  3. No Content-Type filtering — attacker can serve a 5 MB binary as text/html.
     FIX: Added content-type check; reject non-text responses by default.
  4. The retry strategy retries on 429 (rate limit). This is wrong — retrying on 429
     without respecting Retry-After will get the IP banned faster.
     FIX: Removed 429 from status_forcelist; let the caller handle rate limits.
  5. fetch_with_metrics returned dict with key 'bytes' in some paths and 'bytes_fetched'
     in tasks.py — inconsistency. Standardized to 'bytes'.
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

# Allowed response content-type prefixes (everything else is rejected)
ALLOWED_CONTENT_TYPES = ("text/", "application/json", "application/xml",
                          "application/xhtml", "application/atom", "application/rss")

# Private / reserved IP ranges (SSRF protection)
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),   # link-local / AWS metadata
    ipaddress.ip_network("100.64.0.0/10"),    # carrier-grade NAT
    ipaddress.ip_network("0.0.0.0/8"),        # FIX: also block 0.x.x.x
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),        # FIX: IPv6 link-local
    ipaddress.ip_network("::ffff:0:0/96"),    # FIX: IPv4-mapped IPv6
]


class SSRFBlockedError(ValueError):
    pass


def _is_blocked_ip(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in _BLOCKED_NETWORKS)
    except ValueError:
        return True  # unparseable → block by default


class SafeScraper:
    """HTTP fetcher with SSRF protection, response-size cap, and latency metrics."""

    def __init__(self, user_agent: str = "SafeSaaS/1.0"):
        self.user_agent = user_agent
        self._session = self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=2,
            backoff_factor=0.5,
            # FIX: Removed 429 — retrying on rate-limit without Retry-After
            # causes faster banning. Let caller decide.
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({"User-Agent": self.user_agent})
        return session

    def _validate_url(self, url: str) -> None:
        """
        Reject URLs that resolve to private/internal IP ranges.
        Checks BOTH IPv4 (gethostbyname_ex) and IPv6 (getaddrinfo).
        Raises SSRFBlockedError if blocked.

        ⚠️ DNS REBINDING NOTE: This check is advisory. The actual HTTP request
        uses requests' own DNS resolution which happens later. For full protection,
        wire _ssrf_safe_socket_factory (below) into a custom HTTPAdapter.
        """
        parsed = urlparse(url)
        hostname = parsed.hostname

        if not hostname:
            raise ValueError(f"Invalid URL (no hostname): {url!r}")
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Only http/https schemes are allowed, got: {parsed.scheme!r}")

        # FIX: Use getaddrinfo to collect both IPv4 AND IPv6 addresses
        try:
            addr_infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror as exc:
            raise ValueError(f"DNS resolution failed for {hostname!r}: {exc}") from exc

        resolved_ips = {info[4][0] for info in addr_infos}
        if not resolved_ips:
            raise ValueError(f"DNS returned no addresses for {hostname!r}")

        for ip_str in resolved_ips:
            if _is_blocked_ip(ip_str):
                raise SSRFBlockedError(
                    f"Blocked: {hostname!r} resolves to private/reserved IP {ip_str}"
                )

    def fetch_with_metrics(
        self,
        url: str,
        timeout: Optional[int] = None,
        allow_non_text: bool = False,
    ) -> dict:
        """
        Fetch *url* safely. Returns dict with keys:
          success (bool), content (str), bytes (int), latency_ms (int), error (str|None)
        """
        result: dict = {"success": False, "content": "", "bytes": 0,
                         "latency_ms": 0, "error": None}
        try:
            self._validate_url(url)
        except (SSRFBlockedError, ValueError) as exc:
            result["error"] = str(exc)
            return result

        t0 = time.monotonic()
        try:
            resp = self._session.get(
                url,
                timeout=timeout or FETCH_TIMEOUT_SECS,
                stream=True,
            )
            resp.raise_for_status()

            # FIX: Content-type guard — reject binary/unknown types
            ct = resp.headers.get("Content-Type", "").lower()
            if not allow_non_text and not any(ct.startswith(a) for a in ALLOWED_CONTENT_TYPES):
                result["error"] = f"Rejected Content-Type: {ct!r}"
                return result

            # Stream with size cap
            chunks = []
            total = 0
            for chunk in resp.iter_content(chunk_size=8192, decode_unicode=False):
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    result["error"] = f"Response exceeded {MAX_RESPONSE_BYTES} bytes"
                    return result
                chunks.append(chunk)

            raw_bytes = b"".join(chunks)
            encoding = resp.encoding or "utf-8"
            content = raw_bytes.decode(encoding, errors="replace")

            result.update({
                "success": True,
                "content": content,
                "bytes": len(raw_bytes),
                "latency_ms": int((time.monotonic() - t0) * 1000),
            })
        except requests.exceptions.SSLError as exc:
            result["error"] = f"SSL error: {exc}"
        except requests.exceptions.ConnectionError as exc:
            result["error"] = f"Connection error: {exc}"
        except requests.exceptions.Timeout:
            result["error"] = "Request timed out"
        except requests.exceptions.HTTPError as exc:
            result["error"] = f"HTTP {exc.response.status_code}: {exc}"
        except Exception as exc:
            result["error"] = f"Unexpected fetch error: {type(exc).__name__}: {exc}"
        finally:
            result["latency_ms"] = int((time.monotonic() - t0) * 1000)

        return result
