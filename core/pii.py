from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass

from core.config import get_settings
from core.logging import logger


settings = get_settings()

EMAIL_RE = re.compile(r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b")
PHONE_RE = re.compile(r"\+?\d[\d\-\s]{7,}\d")
CARD_RE = re.compile(r"\b\d(?:[\s-]?\d){12,18}\b")


@dataclass
class PIIScrubResult:
    text: str
    count: int


@dataclass
class AIResult:
    available: bool
    error: str | None = None
    spans: list[tuple[int, int, str]] | None = None


def detect_pii_ai(text: str) -> AIResult:
    return AIResult(available=False, error="presidio_not_configured")


def stable_hash(value: str) -> str:
    return hmac.new(
        settings.pii_salt.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _scrub_with_regex(text: str) -> PIIScrubResult:
    count = 0

    def _replace(kind: str):
        def inner(match: re.Match) -> str:
            nonlocal count
            count += 1
            return f"[{kind}:{stable_hash(match.group(0))[:12]}]"
        return inner

    text = EMAIL_RE.sub(_replace("EMAIL"), text)
    text = PHONE_RE.sub(_replace("PHONE"), text)
    text = CARD_RE.sub(_replace("CARD"), text)
    return PIIScrubResult(text=text, count=count)


def scrub_text(text: str, fallback_to_regex: bool = True) -> PIIScrubResult:
    if len(text) > 1_000_000:
        logger.warning("pii.scrub.skipped", reason="input_too_large", security_event=True)
        return PIIScrubResult(text=text, count=0)

    ai_result = detect_pii_ai(text)
    if not ai_result.available:
        if fallback_to_regex:
            logger.warning("pii.presidio_unavailable", fallback="regex_only", security_event=True)
            result = _scrub_with_regex(text)
        else:
            logger.error("pii.presidio_failed", error=ai_result.error, security_event=True)
            raise RuntimeError(f"PII scrubbing unavailable: {ai_result.error}")
    else:
        result = PIIScrubResult(text=text, count=0)

    if result.count > 0:
        logger.warning(
            "pii.scrubbed",
            count=result.count,
            mode="hash",
            security_event=True,
        )
    return result
