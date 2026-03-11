from core.pii import PIIScrubber

def test_email_redaction():
    scrubber = PIIScrubber(mode="redact")
    text = "Contact me at test@example.com"
    clean, count = scrubber.scrub(text)
    assert "[EMAIL]" in clean
    assert count == 1

def test_phone_redaction():
    scrubber = PIIScrubber(mode="redact")
    text = "My number is 555-123-4567"
    clean, count = scrubber.scrub(text)
    assert "[PHONE]" in clean
    assert count == 1
