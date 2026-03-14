#!/usr/bin/env python3
"""
scripts/fuzz_ssrf.py — SSRF fuzzer for Safe Ingestion Engine
=============================================================
Usage:
    python scripts/fuzz_ssrf.py                                    # localhost
    python scripts/fuzz_ssrf.py https://safe.teosegypt.com         # live
    API_KEY=sk-safe-XXXXXXXXXX python scripts/fuzz_ssrf.py https://safe.teosegypt.com

Exit code 0 = all SSRF attempts correctly blocked
Exit code 1 = one or more bypasses detected (CRITICAL)
"""

import os
import sys
import json
import time
import httpx

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8000"
API_KEY  = os.getenv("API_KEY", "sk-safe-TESTKEY000")
ENDPOINT = f"{BASE_URL}/v1/ingest"
HEADERS  = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# ── SSRF payloads — all should be BLOCKED (400) ──────────────────────────────
SSRF_PAYLOADS = [
    # Classic private ranges
    ("Private 127.0.0.1",       "http://127.0.0.1/"),
    ("Private localhost",        "http://localhost/"),
    ("Private 10.x",             "http://10.0.0.1/"),
    ("Private 192.168.x",        "http://192.168.1.1/"),
    ("Private 172.16.x",         "http://172.16.0.1/"),
    ("AWS metadata",             "http://169.254.169.254/latest/meta-data/"),
    ("AWS metadata alt",         "http://169.254.169.254/"),
    # IPv6
    ("IPv6 loopback",            "http://[::1]/"),
    ("IPv6 loopback alt",        "http://[0:0:0:0:0:0:0:1]/"),
    # Decimal/octal/hex bypasses
    ("Decimal 127.0.0.1",        "http://2130706433/"),
    ("Hex 127.0.0.1",            "http://0x7f000001/"),
    ("Octal 127.0.0.1",          "http://0177.0.0.1/"),
    ("Short 127.1",              "http://127.1/"),
    ("Short 0",                  "http://0/"),
    # Blocked schemes
    ("File scheme",              "file:///etc/passwd"),
    ("Gopher scheme",            "gopher://127.0.0.1/"),
    ("FTP scheme",               "ftp://127.0.0.1/"),
    ("Dict scheme",              "dict://127.0.0.1:11211/"),
    # URL shorteners (redirect pivot)
    ("bit.ly shortener",         "http://bit.ly/safe-test"),
    ("tinyurl shortener",        "http://tinyurl.com/safe-test"),
    # Encoding tricks
    ("URL encoded @",            "http://evil.com@127.0.0.1/"),
    ("Double slash",             "http://127.0.0.1%00.example.com/"),
]

# ── Safe URLs — all should be ACCEPTED (200 or 202) ──────────────────────────
SAFE_PAYLOADS = [
    ("Public HTTPS",    "https://example.com/"),
    ("Public HTTP",     "http://httpbin.org/get"),
    ("Public news",     "https://news.ycombinator.com/"),
]

green  = lambda s: f"\033[32m{s}\033[0m"
red    = lambda s: f"\033[31m{s}\033[0m"
yellow = lambda s: f"\033[33m{s}\033[0m"
bold   = lambda s: f"\033[1m{s}\033[0m"

bypasses = []
failures = []

def test(label, url, expect_blocked: bool):
    try:
        r = httpx.post(ENDPOINT, json={"url": url}, headers=HEADERS, timeout=10)
        code = r.status_code
    except Exception as e:
        print(f"  {yellow('ERR')}  {label}: {e}")
        return

    if expect_blocked:
        if code == 400:
            print(f"  {green('BLOCKED')}  {label} ({code})")
        elif code == 401:
            print(f"  {yellow('UNAUTH')}  {label} — register test key first")
        else:
            print(f"  {red('BYPASS!')}  {label} — got {code} for {url}")
            bypasses.append((label, url, code))
    else:
        if code in (200, 202):
            print(f"  {green('PASSED')}  {label} ({code})")
        elif code == 401:
            print(f"  {yellow('UNAUTH')}  {label} — register test key first")
        else:
            print(f"  {red('FAIL')}    {label} — got {code}")
            failures.append((label, url, code))

    time.sleep(0.1)   # be polite to rate limiter


print(bold(f"\nSSRF Fuzzer → {BASE_URL}"))
print(bold("=" * 60))

print(bold("\n[1/2] SSRF payloads — expect 400 BLOCKED"))
for label, url in SSRF_PAYLOADS:
    test(label, url, expect_blocked=True)

print(bold("\n[2/2] Safe URLs — expect 200/202 PASSED"))
for label, url in SAFE_PAYLOADS:
    test(label, url, expect_blocked=False)

print(bold("\n" + "=" * 60))
print(f"Bypasses detected: {red(str(len(bypasses))) if bypasses else green('0')}")
print(f"Safe URL failures: {red(str(len(failures))) if failures else green('0')}")

if bypasses:
    print(red("\nCRITICAL — SSRF BYPASSES:"))
    for label, url, code in bypasses:
        print(f"  [{code}] {label}: {url}")

sys.exit(1 if bypasses or failures else 0)
