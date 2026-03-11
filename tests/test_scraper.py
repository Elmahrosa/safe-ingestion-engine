import pytest
from collectors.scraper import SafeScraper, SSRFBlockedError

def test_ssrf_protection_blocks_localhost():
    scraper = SafeScraper()
    # Should block 127.0.0.1
    with pytest.raises(SSRFBlockedError):
        scraper._validate_url("http://127.0.0.1/admin")

def test_ssrf_protection_blocks_private_ip():
    scraper = SafeScraper()
    # Should block 192.168.x.x
    with pytest.raises(SSRFBlockedError):
        scraper._validate_url("http://192.168.1.1/config")

def test_ssrf_allows_public():
    scraper = SafeScraper()
    # Should not raise
    try:
        scraper._validate_url("https://google.com")
    except SSRFBlockedError:
        pytest.fail("Public URL should not be blocked")
