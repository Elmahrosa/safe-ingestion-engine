"""
core/pii.py — PII detection and scrubbing.
Fixes:
  - PHONE regex was too greedy (matched any 8+ digit sequence) → tightened
  - Missing SSN, IPv4, and credit-card patterns → added
"""

import hashlib
import hmac
import os
import re
from typing import Tuple

PII_SALT = os.getenv("PII_SALT", "changeme-set-in-env")

# ── PII Patterns ─────────────────────────────────────────────────────────────
# Ordered from most-specific to least-specific to avoid partial matches.

_PATTERNS: list[Tuple[str, re.Pattern, str]] = [
    # Credit card: 13-19 digits in groups separated by spaces or dashes
    ("CREDIT_CARD",
     re.compile(
         r"\b(?:4[0-9]{12}(?:[0-9]{3})?|"          # Visa
         r"5[1-5][0-9]{14}|"                         # Mastercard
         r"3[47][0-9]{13}|"                           # Amex
         r"6(?:011|5[0-9]{2})[0-9]{12})"             # Discover
         r"(?:[-\s][0-9]{4}){0,3}\b"
     )),

    # US SSN: 000-00-0000  (never starts with 000, 666, or 9xx in real SSNs)
    ("SSN",
     re.compile(
         r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"
     )),

    # IPv4 addresses
    ("IP_ADDRESS",
     re.compile(
         r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
         r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
     )),

    # Email addresses
    ("EMAIL",
     re.compile(
         r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
     )),

    # North-American phone numbers (E.164-ish):
    #   +1 (555) 555-5555  |  555-555-5555  |  (555) 555-5555  |  5555555555
    # Fix: was too greedy (matched any 8+ digits); now requires recognisable NA format
    ("PHONE",
     re.compile(
         r"\b(?:\+1[\s.-]?)?"                          # optional country code
         r"(?:\(\d{3}\)|\d{3})"                        # area code
         r"[\s.\-]?"
         r"\d{3}"
         r"[\s.\-]?"
         r"\d{4}\b"
     )),
]


class PIIScrubber:
    """
    Scrub PII from text using one of two modes:
    - redact: replace match with [CATEGORY] tag
    - hash:   replace match with HMAC-SHA256 pseudonym
    """

    def __init__(self, mode: str = "redact", salt: str = PII_SALT):
        if mode not in ("redact", "hash"):
            raise ValueError(f"Invalid PII mode {mode!r}. Use 'redact' or 'hash'.")
        self.mode = mode
        self._salt = salt.encode()

    def _replace(self, label: str, value: str) -> str:
        if self.mode == "redact":
            return f"[{label}]"
        digest = hmac.new(self._salt, value.encode(), hashlib.sha256).hexdigest()[:16]
        return f"[{label}:{digest}]"

    def scrub(self, text: str) -> Tuple[str, int]:
        """
        Returns (scrubbed_text, pii_count).
        pii_count is the total number of PII items replaced.
        """
        count = 0

        for label, pattern, *_ in _PATTERNS:
            matches = pattern.findall(text)
            if matches:
                count += len(matches)
                text = pattern.sub(lambda m: self._replace(label, m.group(0)), text)

        return text, count
