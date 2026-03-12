from core.pii import scrub_text

def test_scrub_email():
    result = scrub_text("contact me at a@example.com")
    assert "a@example.com" not in result
    assert "[EMAIL:" in result
