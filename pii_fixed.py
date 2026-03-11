"""
core/pii.py — PII detection and scrubbing.

FIXES APPLIED:
  1. CRITICAL BUG: hmac.new() does not exist — correct function is hmac.new() → NO: it's hmac.new()
     ACTUAL Python API: hmac.new(key, msg, digestmod) — this IS correct in Python 3.
     BUT: the original code does hmac.new(...) which IS valid. 
     REAL BUG FOUND: PIIScrubber.__init__ calls salt.encode() on PII_SALT which may be None
     when PII_SALT env var is not set → AttributeError: 'NoneType' has no attribute 'encode'
     FIX: Raise at construction time with a clear message, not silently at scrub time.
  2. PII_SALT fallback "changeme-set-in-env" removed — if missing, fail loudly at startup.
  3. PHONE regex: the original already had the fix; kept.
  4. scrub() iterates _PATTERNS but the tuple is (label, pattern, *_) — the *_ swallows
     extra positional args silently. Removed placeholder, made explicit.
  5. No international email TLD coverage issue documented (informational, not a code fix).
"""

import hashlib
import hmac
import os
import re
from typing import Tuple

# FIX: Never fall back to a default salt. If PII_SALT is not set, raise at import
# time so operators discover the misconfiguration at startup, not in production.
_RAW_SALT = os.getenv("PII_SALT")
if not _RAW_SALT:
    raise EnvironmentError(
        "PII_SALT environment variable is not set. "
        "Set it to a random secret (e.g. openssl rand -hex 32) before starting the service."
    )

PII_SALT: str = _RAW_SALT

# ── PII Patterns ──────────────────────────────────────────────────────────────
# Ordered from most-specific to least-specific to avoid partial matches.

_PATTERNS: list[Tuple[str, re.Pattern]] = [
    # Credit card: major card types
    ("CREDIT_CARD",
     re.compile(
         r"\b(?:4[0-9]{12}(?:[0-9]{3})?|"          # Visa
         r"5[1-5][0-9]{14}|"                         # Mastercard
         r"3[47][0-9]{13}|"                           # Amex
         r"6(?:011|5[0-9]{2})[0-9]{12})"             # Discover
         r"(?:[-\s][0-9]{4}){0,3}\b"
     )),

    # US SSN: never starts with 000, 666, or 9xx
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

    # North-American phone numbers (E.164-ish)
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
    - hash:   replace match with HMAC-SHA256 pseudonym (first 16 hex chars)
    """

    def __init__(self, mode: str = "redact", salt: str = PII_SALT):
        if mode not in ("redact", "hash"):
            raise ValueError(f"Invalid PII mode {mode!r}. Use 'redact' or 'hash'.")
        # FIX: Validate salt is a non-empty string before encoding
        if not salt or not isinstance(salt, str):
            raise ValueError("PII salt must be a non-empty string.")
        self.mode = mode
        self._salt = salt.encode()

    def _replace(self, label: str, value: str) -> str:
        if self.mode == "redact":
            return f"[{label}]"
        # hmac.new is the correct Python 3 API
        digest = hmac.new(self._salt, value.encode(), hashlib.sha256).hexdigest()[:16]
        return f"[{label}:{digest}]"

    def scrub(self, text: str) -> Tuple[str, int]:
        """
        Returns (scrubbed_text, pii_count).
        pii_count is the total number of PII items replaced.
        """
        count = 0
        for label, pattern in _PATTERNS:  # FIX: explicit 2-tuple, no *_ slop
            matches = pattern.findall(text)
            if matches:
                count += len(matches)
                text = pattern.sub(
                    lambda m, lbl=label: self._replace(lbl, m.group(0)), text
                )
        return text, count
