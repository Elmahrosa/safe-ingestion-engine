"""
tests/test_security.py — Unit tests for all audit findings
===========================================================
Covers CVSS 8.2 (SSRF), CVSS 7.5 (job enum), CVSS 6.5 (auth)
"""

import pytest
from fastapi import HTTPException
from core.security import ssrf_safe_url, assert_job_owner


# ── SSRF — must block (CVSS 8.2) ──────────────────────────────────────────────
@pytest.mark.parametrize("url", [
    "http://127.0.0.1/",
    "http://127.0.0.1/etc/passwd",
    "http://localhost/",
    "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.1/internal",
    "http://192.168.1.1/admin",
    "http://172.16.0.1/",
    "http://[::1]/",
    "http://[0:0:0:0:0:0:0:1]/",
    "http://2130706433/",         # decimal 127.0.0.1
    "http://0x7f000001/",         # hex 127.0.0.1
    "http://127.1/",              # short form
    "http://0/",                  # 0.0.0.0
    "file:///etc/passwd",
    "gopher://127.0.0.1/",
    "ftp://127.0.0.1/",
    "dict://127.0.0.1:11211/",
    "http://bit.ly/safe-test",    # URL shortener
    "http://tinyurl.com/test",    # URL shortener
])
def test_ssrf_blocked(url):
    with pytest.raises(HTTPException) as exc:
        ssrf_safe_url(url)
    assert exc.value.status_code == 400


# ── SSRF — must allow (legitimate public URLs) ────────────────────────────────
@pytest.mark.parametrize("url", [
    "https://example.com/page",
    "http://httpbin.org/get",
    "https://news.ycombinator.com",
    "https://api.github.com/repos/octocat/hello-world",
])
def test_ssrf_allowed(url):
    result = ssrf_safe_url(url)
    assert result == url


# ── Job ownership (CVSS 7.5) ──────────────────────────────────────────────────
def test_job_owner_match():
    job = {"api_key": "sk-safe-AAAAAA0000", "status": "done"}
    assert_job_owner(job, "sk-safe-AAAAAA0000")  # no exception


def test_job_owner_mismatch_returns_404():
    job = {"api_key": "sk-safe-AAAAAA0000", "status": "done"}
    with pytest.raises(HTTPException) as exc:
        assert_job_owner(job, "sk-safe-DIFFERENT0")
    assert exc.value.status_code == 404   # 404 not 403 — don't leak existence


def test_job_owner_empty_key():
    job = {"api_key": "", "status": "done"}
    with pytest.raises(HTTPException) as exc:
        assert_job_owner(job, "sk-safe-AAAAAA0000")
    assert exc.value.status_code == 404


def test_job_owner_missing_field():
    job = {"status": "done"}  # no api_key field at all
    with pytest.raises(HTTPException) as exc:
        assert_job_owner(job, "sk-safe-AAAAAA0000")
    assert exc.value.status_code == 404


# ── Auth — hash + constant-time compare ──────────────────────────────────────
def test_hash_key_deterministic():
    from core.auth import hash_key
    assert hash_key("sk-safe-TEST0000") == hash_key("sk-safe-TEST0000")


def test_hash_key_different_inputs_differ():
    from core.auth import hash_key
    assert hash_key("sk-safe-AAAA0000") != hash_key("sk-safe-BBBB0000")


def test_is_valid_key_rejects_empty():
    from core.auth import is_valid_key
    assert is_valid_key("") is False


def test_is_valid_key_rejects_weak_pattern():
    from core.auth import is_valid_key
    # These should not be in Redis during tests
    assert is_valid_key("sk-safe-0000000000") is False
    assert is_valid_key("sk-safe-1111111111") is False
