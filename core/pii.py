"""
core/pii.py — Enterprise PII detection and scrubbing.

Features
--------
• Microsoft Presidio support (NER-based detection)
• Regex fallback when Presidio not installed
• Redaction or HMAC hashing modes
• Deterministic pseudonymization
• IPv4 / Email / Phone / SSN / Credit card detection
"""

import hashlib
import hmac
import os
import re
from typing import Tuple

# ─────────────────────────────────────────────
# Optional Presidio Support
# ─────────────────────────────────────────────

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine

    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False


# ─────────────────────────────────────────────
# Environment
# ─────────────────────────────────────────────

PII_SALT = os.getenv("PII_SALT", "default-dev-salt")


# ─────────────────────────────────────────────
# Regex fallback patterns
# ─────────────────────────────────────────────

_PATTERNS = [

    (
        "CREDIT_CARD",
        re.compile(
            r"\b(?:4[0-9]{12}(?:[0-9]{3})?|"
            r"5[1-5][0-9]{14}|"
            r"3[47][0-9]{13}|"
            r"6(?:011|5[0-9]{2})[0-9]{12})"
            r"(?:[-\s][0-9]{4}){0,3}\b"
        )
    ),

    (
        "SSN",
        re.compile(
            r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"
        )
    ),

    (
        "IP_ADDRESS",
        re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
        )
    ),

    (
        "EMAIL",
        re.compile(
            r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
        )
    ),

    (
        "PHONE",
        re.compile(
            r"\b(?:\+1[\s.-]?)?"
            r"(?:\(\d{3}\)|\d{3})"
            r"[\s.\-]?"
            r"\d{3}"
            r"[\s.\-]?"
            r"\d{4}\b"
        )
    )
]


# ─────────────────────────────────────────────
# PII Scrubber
# ─────────────────────────────────────────────

class PIIScrubber:
    """
    Scrubs PII from text.

    Modes
    -----
    redact : replace with [CATEGORY]
    hash   : replace with deterministic HMAC pseudonym
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

    # ─────────────────────────────────────────

    def _replace(self, label: str, value: str) -> str:

        if self.mode == "redact":
            return f"[{label}]"

        digest = hmac.new(
            self._salt,
            value.encode(),
            hashlib.sha256
        ).hexdigest()[:16]

        return f"[{label}:{digest}]"

    # ─────────────────────────────────────────

    def scrub(self, text: str) -> Tuple[str, int]:
        """
        Returns:
            (scrubbed_text, pii_count)
        """

        count = 0

        # ─────────────────────────
        # Method 1 — Presidio
        # ─────────────────────────

        if self.analyzer:

            results = self.analyzer.analyze(
                text=text,
                language="en"
            )

            count = len(results)

            if count == 0:
                return text, 0

            result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results
            )

            return result.text, count

        # ─────────────────────────
        # Method 2 — Regex fallback
        # ─────────────────────────

        for label, pattern in _PATTERNS:

            matches = pattern.findall(text)

            if not matches:
                continue

            count += len(matches)

            text = pattern.sub(
                lambda m: self._replace(label, m.group(0)),
                text
            )

        return text, count
