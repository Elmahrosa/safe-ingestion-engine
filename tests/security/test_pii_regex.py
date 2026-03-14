import time

from core.pii import CARD_RE, scrub_text


def test_card_regex_completes_quickly():
    payload = "1" + " -" * 5000 + "2"
    start = time.time()
    CARD_RE.findall(payload)
    elapsed = time.time() - start
    assert elapsed < 1.0


def test_scrub_large_input_skips():
    result = scrub_text("a" * 1_000_001)
    assert result.count == 0
