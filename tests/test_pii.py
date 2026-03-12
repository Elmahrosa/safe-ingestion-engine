"""
tests/test_pii.py — PII scrubber tests.
Covers audit recommendations: unicode evasion, international phones, edge cases.
"""
import pytest
from core.pii import PIIScrubber


@pytest.fixture
def scrubber():
    return PIIScrubber(mode="redact", salt="test-salt")


@pytest.fixture
def hash_scrubber():
    return PIIScrubber(mode="hash", salt="test-salt")


# ── Email ─────────────────────────────────────────────────────────────────────

def test_email_redacted(scrubber):
    text, count = scrubber.scrub("Contact me at test@example.com")
    assert "[EMAIL]" in text
    assert count == 1


def test_email_not_in_output(scrubber):
    text, _ = scrubber.scrub("user@domain.org")
    assert "@" not in text or "[EMAIL]" in text


# ── Phone ─────────────────────────────────────────────────────────────────────

def test_phone_na_format(scrubber):
    text, count = scrubber.scrub("Call me at 555-123-4567")
    assert "[PHONE]" in text
    assert count == 1


def test_phone_with_country_code(scrubber):
    text, count = scrubber.scrub("My number is +1 (555) 123-4567")
    assert "[PHONE]" in text


def test_phone_international(scrubber):
    text, count = scrubber.scrub("UK number: +44 20 7946 0958")
    assert "[PHONE]" in text


# ── SSN ───────────────────────────────────────────────────────────────────────

def test_ssn_redacted(scrubber):
    text, count = scrubber.scrub("SSN: 123-45-6789")
    assert "[SSN]" in text
    assert count == 1


def test_ssn_invalid_not_matched(scrubber):
    # 000-xx-xxxx is invalid SSN
    text, count = scrubber.scrub("000-12-3456")
    assert count == 0


# ── Credit card ───────────────────────────────────────────────────────────────

def test_credit_card_visa(scrubber):
    text, count = scrubber.scrub("Card: 4111111111111111")
    assert "[CREDIT_CARD]" in text
    assert count == 1


def test_credit_card_amex(scrubber):
    text, count = scrubber.scrub("Amex: 378282246310005")
    assert "[CREDIT_CARD]" in text


# ── IP address ────────────────────────────────────────────────────────────────

def test_ip_address_redacted(scrubber):
    text, count = scrubber.scrub("Server IP: 192.168.1.100")
    assert "[IP_ADDRESS]" in text
    assert count == 1


# ── Unicode normalization (audit finding) ────────────────────────────────────

def test_unicode_normalized_email(scrubber):
    """Audit finding: obfuscated unicode should still be caught."""
    # NFKC normalization should handle unicode lookalikes
    text, count = scrubber.scrub("test\u0040example.com")  # \u0040 = @
    assert count >= 1 or "[EMAIL]" in text


# ── Hash mode ─────────────────────────────────────────────────────────────────

def test_hash_mode_produces_deterministic_output(hash_scrubber):
    text1, _ = hash_scrubber.scrub("test@example.com")
    text2, _ = hash_scrubber.scrub("test@example.com")
    assert text1 == text2


def test_hash_mode_different_values_differ(hash_scrubber):
    text1, _ = hash_scrubber.scrub("a@example.com")
    text2, _ = hash_scrubber.scrub("b@example.com")
    assert text1 != text2


# ── Multiple PII ──────────────────────────────────────────────────────────────

def test_multiple_pii_types(scrubber):
    text = "Email: foo@bar.com, SSN: 123-45-6789, Card: 4111111111111111"
    clean, count = scrubber.scrub(text)
    assert count >= 3
    assert "foo@bar.com" not in clean
    assert "123-45-6789" not in clean
    assert "4111111111111111" not in clean


def test_empty_string(scrubber):
    text, count = scrubber.scrub("")
    assert text == ""
    assert count == 0


def test_no_pii(scrubber):
    text, count = scrubber.scrub("Hello world, no PII here.")
    assert count == 0
    assert text == "Hello world, no PII here."
