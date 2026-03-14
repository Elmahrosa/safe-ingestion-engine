"""
core/security.py — Defence-in-depth security helpers
======================================================
Covers:
  CVSS 8.2  SSRF              -> ssrf_safe_url() with redirect + shortener guard
  CVSS 7.5  Job enumeration   -> assert_job_owner()
  CVSS 6.5  Auth brute-force  -> RATE_* constants for slowapi
  NEW       Redirect SSRF     -> follow_redirects=False enforced in HttpConnector
  NEW       0.0.0.0 / 127.1   -> all bypass variants blocked
"""

import ipaddress
import os
import socket
from urllib.parse import urlparse

from fastapi import HTTPException

_PRIVATE_NETS = [
    ipaddress.ip_network(n) for n in [
        "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10",
        "127.0.0.0/8", "169.254.0.0/16", "172.16.0.0/12",
        "192.0.0.0/24", "192.168.0.0/16", "198.18.0.0/15",
        "198.51.100.0/24", "203.0.113.0/24", "224.0.0.0/4",
        "240.0.0.0/4", "255.255.255.255/32",
        "::1/128", "fc00::/7", "fe80::/10", "ff00::/8",
    ]
]
_BLOCKED_SCHEMES = {"file", "ftp", "gopher", "dict", "ldap", "ldaps", "jar"}
_ALLOWED_SCHEMES = {"http", "https"}

# URL shorteners commonly used to pivot to internal addresses
_BLOCKED_HOSTS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly",
    "buff.ly", "short.io", "rebrand.ly", "is.gd", "v.gd",
}


def _is_private_ip(host: str) -> bool:
    # Strip brackets (IPv6 literal) and trailing dots
    host = host.strip("[]").rstrip(".")
    try:
        addr = ipaddress.ip_address(host)
        return any(addr in net for net in _PRIVATE_NETS)
    except ValueError:
        pass
    try:
        results = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return True  # unresolvable = unsafe
    for _, _, _, _, sockaddr in results:
        try:
            addr = ipaddress.ip_address(sockaddr[0])
            if any(addr in net for net in _PRIVATE_NETS):
                return True
        except ValueError:
            return True
    return False


def ssrf_safe_url(raw_url: str) -> str:
    """
    Full SSRF validation including:
      - scheme allowlist
      - URL shortener blocklist
      - private IP / reserved range check
      - decimal IP, IPv6, alternate encoding detection
    Raises HTTP 400 on any violation.
    """
    try:
        parsed = urlparse(raw_url)
    except Exception:
        raise HTTPException(400, "Malformed URL.")

    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise HTTPException(400, f"Scheme '{scheme}' not allowed.")

    host = (parsed.hostname or "").lower()
    if not host:
        raise HTTPException(400, "URL has no host.")

    # Block known URL shorteners (redirect SSRF vector)
    if host in _BLOCKED_HOSTS or any(host.endswith("." + b) for b in _BLOCKED_HOSTS):
        raise HTTPException(400, "URL shorteners are not permitted.")

    # Catch alternate 127.0.0.1 forms: 127.1, 0, 2130706433, 0x7f000001
    for alt in [host, host.replace(".", "")]:
        try:
            addr = ipaddress.ip_address(int(alt, 0) if alt.startswith("0x") else int(alt))
            if any(addr in net for net in _PRIVATE_NETS):
                raise HTTPException(400, "URL resolves to a private/reserved address.")
        except (ValueError, OverflowError):
            pass

    if _is_private_ip(host):
        raise HTTPException(400, "URL resolves to a private/reserved address.")

    return raw_url


def assert_job_owner(job_data: dict, api_key: str) -> None:
    """404 (not 403) on cross-key job access — avoids confirming job exists."""
    if job_data.get("api_key", "") != api_key:
        raise HTTPException(404, "Job not found or expired.")


RATE_INGEST = os.getenv("RATE_INGEST", "60/minute")
RATE_AUTH   = os.getenv("RATE_AUTH",   "20/minute")
RATE_GLOBAL = os.getenv("RATE_GLOBAL", "200/minute")
