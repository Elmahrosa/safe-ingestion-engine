import hashlib
import hmac
import re

from core.config import get_settings
from core.logging import logger

settings = get_settings()

EMAIL_RE = re.compile(r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b")
PHONE_RE = re.compile(r"\+?\d[\d\-\s]{7,}\d")
CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

def stable_hash(value: str) -> str:
    return hmac.new(settings.pii_salt.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()

def scrub_text(text: str) -> str:
    original = text
    text = EMAIL_RE.sub(lambda m: f"[EMAIL:{stable_hash(m.group(0))[:12]}]", text)
    text = PHONE_RE.sub(lambda m: f"[PHONE:{stable_hash(m.group(0))[:12]}]", text)
    text = CARD_RE.sub(lambda m: f"[CARD:{stable_hash(m.group(0))[:12]}]", text)
    if text != original:
        logger.warning("pii.scrubbed")
    return text
