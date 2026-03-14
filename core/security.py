"""
core/security.py
================
Defence-in-depth helpers addressing audit findings:

  - SSRF guard (private IPs, IPv6, decimal/octal bypasses, xip.io tricks)
  - URL allowlist/blocklist validation
  - Job ownership scoping (prevent cross-key job enumeration)
  - Rate-limit key for slowapi middleware

Audit refs
----------
  CVSS 8.2  — SSRF in URL ingestion          → ssrf_safe_url()
  CVSS 7.5  — Job ID enumeration             → assert_job_owner()
  CVSS 6.5  — Auth brute-force / rate limits → RATE_LIMIT constants
"""

import ipaddress
import os
import socket
from urllib.parse import urlparse

from fastapi import HTTPException, status


# ── SSRF guard ────────────────────────────────────────────────────────────────

_PRIVATE_NETS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),   # AWS metadata, link-local
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),      # multicast
    ipaddress.ip_network("240.0.0.0/4"),      # reserved
    ipaddress.ip_network("255.255.255.255/32"),
    # IPv6
    ipaddress.ip_network("::1/128"),           # loopback
    ipaddress.ip_network("fc00::/7"),          # ULA
    ipaddress.ip_network("fe80::/10"),         # link-local
    ipaddress.ip_network("ff00::/8"),          # multicast
]

_BLOCKED_SCHEMES = {"file", "ftp", "gopher", "dict", "ldap", "ldaps", "jar"}
_ALLOWED_SCHEMES = {"http", "https"}


def _is_private_ip(host: str) -> bool:
    """
    Resolve hostname and check all returned IPs against private ranges.
    Handles: decimal IPs (2130706433), xip.io-style, IPv6, etc.
    """
    try:
        # Try parsing as literal IP first (catches decimal/octal tricks)
        addr = ipaddress.ip_address(host)
        return any(addr in net for net in _PRIVATE_NETS)
    except ValueError:
        pass

    # DNS resolve — reject if ANY returned address is private
    try:
        results = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return True  # can't resolve → treat as unsafe

    for result in results:
        af, _, _, _, sockaddr = result
        ip_str = sockaddr[0]
        try:
            addr = ipaddress.ip_address(ip_str)
            if any(addr in net for net in _PRIVATE_NETS):
                return True
        except ValueError:
            return True  # unparseable → treat as unsafe

    return False


def ssrf_safe_url(raw_url: str) -> str:
    """
    Validate a user-supplied URL against SSRF attack vectors.
    Raises HTTP 400 on any violation.
    Returns the original URL if safe.
    """
    try:
        parsed = urlparse(raw_url)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed URL.")

    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise HTTPException(
            status_code=400,
            detail=f"Scheme '{scheme}' not allowed. Use http or https.",
        )

    host = parsed.hostname or ""
    if not host:
        raise HTTPException(status_code=400, detail="URL has no host.")

    # Strip port, brackets (IPv6 literal), and trailing dots
    host = host.strip("[]").rstrip(".")

    if _is_private_ip(host):
        raise HTTPException(
            status_code=400,
            detail="URL resolves to a private/reserved address.",
        )

    return raw_url


# ── Job ownership ─────────────────────────────────────────────────────────────

def assert_job_owner(job_data: dict, api_key: str) -> None:
    """
    Raise 404 (not 403) if the requesting key doesn't own this job.
    Returns 404 to avoid leaking whether the job exists at all.
    """
    owner = job_data.get("api_key", "")
    if owner != api_key:
        raise HTTPException(status_code=404, detail="Job not found or expired.")


# ── Rate limit strings for slowapi ───────────────────────────────────────────
# Usage: @limiter.limit(RATE_INGEST) on the ingest route

RATE_INGEST = os.getenv("RATE_INGEST", "60/minute")
RATE_AUTH   = os.getenv("RATE_AUTH",   "20/minute")
RATE_GLOBAL = os.getenv("RATE_GLOBAL", "200/minute")
