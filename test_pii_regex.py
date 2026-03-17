import time

from core.pii import CARD_RE, scrub_text


def test_card_regex_completes_quickly():
    payload = "1" + " -" * 5000 + "2"
    start = time.time()
    CARD_RE.findall(payload)
    elapsed = time.time() - start
    assert elapsed < 1.0


def test_scrub_large_input_truncates_and_scrubs():
    # New behavior: input > 1MB is TRUNCATED then scrubbed (not skipped).
    # 'a' * 1_000_001 has no PII so count is still 0, but truncated=True.
    result = scrub_text("a" * 1_000_001)
    assert result.count == 0
    assert result.truncated is True


def test_scrub_large_input_with_pii_still_scrubs():
    # PII within first 1MB must be scrubbed even on oversized input.
    # Put an email at position 0, then pad to > 1MB.
    text = "contact@example.com " + "x" * 1_000_001
    result = scrub_text(text)
    assert "contact@example.com" not in result.text
    assert result.count >= 1
    assert result.truncated is True
