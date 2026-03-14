"""
tests/test_security.py
======================
Unit tests covering the three highest-severity audit findings.
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from core.security import ssrf_safe_url, assert_job_owner


# ── SSRF guard tests (CVSS 8.2) ───────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "http://127.0.0.1/etc/passwd",
    "http://localhost/",
    "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.1/internal",
    "http://192.168.1.1/admin",
    "http://172.16.0.1/",
    "http://[::1]/",
    "http://2130706433/",          # decimal IP = 127.0.0.1
    "file:///etc/passwd",
    "ftp://internal-server/",
    "gopher://attacker/",
])
def test_ssrf_blocked(url):
    with pytest.raises(HTTPException) as exc:
        ssrf_safe_url(url)
    assert exc.value.status_code == 400


@pytest.mark.parametrize("url", [
    "https://example.com/page",
    "http://httpbin.org/get",
    "https://news.ycombinator.com",
])
def test_ssrf_allowed(url):
    result = ssrf_safe_url(url)
    assert result == url


# ── Job ownership tests (CVSS 7.5) ────────────────────────────────────────────

def test_job_owner_match():
    job = {"api_key": "sk-safe-AAAAAA0000", "status": "done"}
    assert_job_owner(job, "sk-safe-AAAAAA0000")  # should not raise


def test_job_owner_mismatch():
    job = {"api_key": "sk-safe-AAAAAA0000", "status": "done"}
    with pytest.raises(HTTPException) as exc:
        assert_job_owner(job, "sk-safe-DIFFERENT0")
    assert exc.value.status_code == 404  # 404 not 403 — don't leak existence


def test_job_owner_missing_key():
    job = {"status": "done"}  # no api_key field
    with pytest.raises(HTTPException) as exc:
        assert_job_owner(job, "sk-safe-AAAAAA0000")
    assert exc.value.status_code == 404
