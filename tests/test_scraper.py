"""
tests/test_scraper.py — SafeScraper SSRF protection tests.
Covers audit recommendations: IPv6, metadata endpoint, all RFC1918 ranges.
"""
import pytest
from collectors.scraper import SafeScraper, SSRFBlockedError


@pytest.fixture
def scraper():
    return SafeScraper()


# ── Blocked: loopback ────────────────────────────────────────────────────────

def test_blocks_localhost(scraper):
    with pytest.raises(SSRFBlockedError):
        scraper._validate_url("http://127.0.0.1/admin")


def test_blocks_localhost_named(scraper):
    with pytest.raises((SSRFBlockedError, ValueError)):
        scraper._validate_url("http://localhost/secret")


# ── Blocked: private IPv4 ranges ─────────────────────────────────────────────

def test_blocks_192_168(scraper):
    with pytest.raises(SSRFBlockedError):
        scraper._validate_url("http://192.168.1.1/config")


def test_blocks_10_x(scraper):
    with pytest.raises(SSRFBlockedError):
        scraper._validate_url("http://10.0.0.1/internal")


def test_blocks_172_16(scraper):
    with pytest.raises(SSRFBlockedError):
        scraper._validate_url("http://172.16.0.1/private")


def test_blocks_172_31(scraper):
    with pytest.raises(SSRFBlockedError):
        scraper._validate_url("http://172.31.255.255/")


# ── Blocked: AWS/cloud metadata endpoint ────────────────────────────────────

def test_blocks_aws_metadata(scraper):
    with pytest.raises(SSRFBlockedError):
        scraper._validate_url("http://169.254.169.254/latest/meta-data/")


def test_blocks_link_local(scraper):
    with pytest.raises(SSRFBlockedError):
        scraper._validate_url("http://169.254.0.1/")


# ── Blocked: IPv6 loopback ────────────────────────────────────────────────────

def test_blocks_ipv6_loopback(scraper):
    with pytest.raises((SSRFBlockedError, ValueError)):
        scraper._validate_url("http://[::1]/admin")


# ── Blocked: scheme ───────────────────────────────────────────────────────────

def test_blocks_file_scheme(scraper):
    with pytest.raises(ValueError):
        scraper._validate_url("file:///etc/passwd")


def test_blocks_ftp_scheme(scraper):
    with pytest.raises(ValueError):
        scraper._validate_url("ftp://example.com/file")


def test_blocks_gopher_scheme(scraper):
    with pytest.raises(ValueError):
        scraper._validate_url("gopher://example.com/")


# ── Allowed: public IPs ───────────────────────────────────────────────────────

def test_allows_google(scraper):
    """Public domains should not be blocked."""
    try:
        scraper._validate_url("https://google.com")
    except SSRFBlockedError:
        pytest.fail("Public URL should not be blocked")


def test_allows_example_com(scraper):
    try:
        scraper._validate_url("https://example.com")
    except SSRFBlockedError:
        pytest.fail("example.com should not be blocked")


# ── Invalid URLs ──────────────────────────────────────────────────────────────

def test_rejects_no_hostname(scraper):
    with pytest.raises(ValueError):
        scraper._validate_url("https://")


def test_rejects_empty_url(scraper):
    with pytest.raises(ValueError):
        scraper._validate_url("")
