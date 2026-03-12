import hashlib
import hmac
import re

from core.config import get_settings
from core.logging import logger


settings = get_settings()

EMAIL_RE = re.compile(r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b")
PHONE_RE = re.compile(r"\+?\d[\d\-\s]{7,}\d")
CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


class PIIScrubber:
    def __init__(self, mode: str = "hash"):
        self.mode = mode

    def _stable_hash(self, value: str) -> str:
        return hmac.new(
            settings.pii_salt.encode("utf-8"),
            value.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def scrub(self, text: str) -> tuple[str, int]:
        count = 0

        def repl_email(m):
            nonlocal count
            count += 1
            return f"[EMAIL:{self._stable_hash(m.group(0))[:12]}]"

        def repl_phone(m):
            nonlocal count
            count += 1
            return f"[PHONE:{self._stable_hash(m.group(0))[:12]}]"

        def repl_card(m):
            nonlocal count
            count += 1
            return f"[CARD:{self._stable_hash(m.group(0))[:12]}]"

        original = text
        text = EMAIL_RE.sub(repl_email, text)
        text = PHONE_RE.sub(repl_phone, text)
        text = CARD_RE.sub(repl_card, text)

        if text != original:
            logger.warning("pii.scrubbed", count=count)

        return text, count


def scrub_text(text: str) -> str:
    scrubber = PIIScrubber(mode="hash")
    cleaned, _ = scrubber.scrub(text)
    return cleaned
