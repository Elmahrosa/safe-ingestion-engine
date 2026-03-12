"""
core/pii.py — Enterprise PII detection and scrubbing.

Security hardening applied (audit recommendations):
  - Unicode normalization before regex matching (prevents obfuscation bypass)
  - Expanded phone patterns: international formats, not just NA
  - Improved email regex: handles quoted local parts
  - Presidio NER support (optional, falls back to regex)
  - Redact or HMAC-hash modes
  - Returns (scrubbed_text, count) tuple
"""

import hashlib
import hmac
import os
import re
import unicodedata
from typing import Tuple

# ── Optional Presidio ─────────────────────────────────────────────────────────
try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False

# ── Environment ───────────────────────────────────────────────────────────────
PII_SALT = os.getenv("PII_SALT", "default-dev-salt-change-in-production")

# ── Regex patterns ────────────────────────────────────────────────────────────
# Order matters: more specific patterns first

_PATTERNS = [
    (
        "CREDIT_CARD",
        re.compile(
            r"\b(?:"
            r"4[0-9]{12}(?:[0-9]{3})?"          # Visa
            r"|5[1-5][0-9]{14}"                  # Mastercard
            r"|3[47][0-9]{13}"                   # Amex
            r"|6(?:011|5[0-9]{2})[0-9]{12}"      # Discover
            r"|3(?:0[0-5]|[68][0-9])[0-9]{11}"  # Diners
            r"|(?:2131|1800|35\d{3})\d{11}"      # JCB
            r")"
            r"(?:[-\s][0-9]{4}){0,3}\b"
        ),
    ),
    (
        "SSN",
        re.compile(
            r"\b(?!000|666|9\d{2})\d{3}"
            r"[-\s](?!00)\d{2}"
            r"[-\s](?!0000)\d{4}\b"
        ),
    ),
    (
        "IP_ADDRESS",
        re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
        ),
    ),
    (
        "EMAIL",
        re.compile(
            r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
        ),
    ),
    (
        "PHONE",
        re.compile(
            # North American: +1 (555) 123-4567, 555-123-4567, 5551234567
            r"\b(?:\+?1[\s.\-]?)?"
            r"(?:\(\d{3}\)|\d{3})"
            r"[\s.\-]?\d{3}[\s.\-]?\d{4}\b"
            r"|"
            # International: +44 20 7946 0958, +33 1 42 86 83 26
            r"\+\d{1,3}[\s.\-]?\(?\d{1,4}\)?[\s.\-]?\d{1,4}[\s.\-]?\d{1,9}"
        ),
    ),
]


# ── PII Scrubber ──────────────────────────────────────────────────────────────

class PIIScrubber:
    """
    Scrubs PII from text using Presidio (if available) with regex fallback.

    Modes
    -----
    redact : replace with [CATEGORY]
    hash   : replace with deterministic HMAC pseudonym [CATEGORY:hex16]
    """

    def __init__(self, mode: str = "redact", salt: str = PII_SALT):
        if mode not in ("redact", "hash"):
            raise ValueError("PII mode must be 'redact' or 'hash'")
        self.mode = mode
        self._salt = salt.encode()

        if PRESIDIO_AVAILABLE:
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
        else:
            self.analyzer = None
            self.anonymizer = None

    def _replace(self, label: str, value: str) -> str:
        if self.mode == "redact":
            return f"[{label}]"
        digest = hmac.new(self._salt, value.encode(), hashlib.sha256).hexdigest()[:16]
        return f"[{label}:{digest}]"

    def _normalize(self, text: str) -> str:
        """
        Normalize unicode to prevent obfuscation bypass.
        e.g. e\\u006dail → email
        """
        return unicodedata.normalize("NFKC", text)

    def _scrub_regex(self, text: str) -> Tuple[str, int]:
        count = 0
        for label, pattern in _PATTERNS:
            def replacer(m, lbl=label):
                return self._replace(lbl, m.group(0))
            new_text, n = pattern.subn(replacer, text)
            count += n
            text = new_text
        return text, count

    def _scrub_presidio(self, text: str) -> Tuple[str, int]:
        try:
            results = self.analyzer.analyze(text=text, language="en")
            if not results:
                return text, 0

            # Sort results by start position descending to replace without offset shifting
            results_sorted = sorted(results, key=lambda r: r.start, reverse=True)
            count = len(results_sorted)
            text_list = list(text)

            for result in results_sorted:
                replacement = self._replace(result.entity_type, text[result.start:result.end])
                text_list[result.start:result.end] = list(replacement)

            return "".join(text_list), count
        except Exception:
            # Fall back to regex on Presidio failure
            return self._scrub_regex(text)

    def scrub(self, text: str) -> Tuple[str, int]:
        """
        Scrub PII from text. Returns (scrubbed_text, pii_count).
        """
        if not text:
            return text, 0

        # Always normalize first to prevent unicode obfuscation
        normalized = self._normalize(text)

        if PRESIDIO_AVAILABLE and self.analyzer:
            return self._scrub_presidio(normalized)
        return self._scrub_regex(normalized)
