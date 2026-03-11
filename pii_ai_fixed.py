"""
core/pii_ai.py — AI-powered PII detection via Microsoft Presidio.

FIXES APPLIED:
  1. AnalyzerEngine() is re-instantiated on every call — it loads NLP models (~500ms each).
     FIX: Cache the engine at module level with lazy init (thread-safe via a lock).
  2. Broad except Exception swallows real bugs (e.g. OOM, assertion errors in spaCy).
     FIX: Re-raise unexpected exceptions; only suppress ImportError and known Presidio errors.
  3. No confidence threshold filtering — low-confidence (0.3) detections create false positives.
     FIX: Added min_score parameter with default 0.5.
  4. Presidio AnalyzerEngine called without specifying entities — defaults to all, very slow.
     FIX: Accept optional entities list; default to most common types.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

_analyzer_lock = threading.Lock()
_analyzer_instance = None  # FIX: module-level cache


def _get_analyzer():
    """Lazy-init and cache the AnalyzerEngine. Thread-safe."""
    global _analyzer_instance
    if _analyzer_instance is None:
        with _analyzer_lock:
            if _analyzer_instance is None:  # double-checked locking
                from presidio_analyzer import AnalyzerEngine
                _analyzer_instance = AnalyzerEngine()
    return _analyzer_instance


@dataclass
class AIPiiResult:
    entities: List[Dict[str, Any]] = field(default_factory=list)
    available: bool = False
    error: Optional[str] = None


# Default entity types to scan for (subset is faster than scanning all)
DEFAULT_ENTITIES = [
    "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "US_SSN",
    "IP_ADDRESS", "PERSON", "LOCATION", "DATE_TIME",
]


def detect_pii_ai(
    text: str,
    min_score: float = 0.5,
    entities: Optional[List[str]] = None,
) -> AIPiiResult:
    """
    Uses Presidio Analyzer if installed. Returns AIPiiResult.

    Args:
        text:      Input text to scan.
        min_score: Minimum confidence score (0.0–1.0) to include an entity. Default 0.5.
        entities:  Entity types to detect. Defaults to DEFAULT_ENTITIES.
    """
    if not text or not text.strip():
        return AIPiiResult(entities=[], available=True)

    try:
        analyzer = _get_analyzer()
    except ImportError:
        return AIPiiResult(available=False, error="Presidio not installed. "
                           "Run: pip install presidio-analyzer presidio-anonymizer")

    try:
        results = analyzer.analyze(
            text=text,
            language="en",
            entities=entities or DEFAULT_ENTITIES,
            score_threshold=min_score,  # FIX: filter low-confidence hits in Presidio directly
        )
        ents = [
            {
                "type": r.entity_type,
                "score": round(float(r.score), 3),
                "start": int(r.start),
                "end": int(r.end),
                "value": text[r.start:r.end],  # include matched value for downstream use
            }
            for r in results
            if r.score >= min_score
        ]
        return AIPiiResult(entities=ents, available=True)

    except ImportError:
        # FIX: ImportError mid-analysis (e.g. missing spaCy model) — distinct from startup ImportError
        return AIPiiResult(available=False, error="Presidio language model not loaded. "
                           "Run: python -m spacy download en_core_web_lg")
    except ValueError as exc:
        # FIX: ValueError from Presidio for invalid entity types — not a crash, report it
        return AIPiiResult(available=False, error=f"Presidio configuration error: {exc}")
    # NOTE: We do NOT catch generic Exception here. Unexpected errors (OOM, assertion
    # failures, etc.) should propagate so the caller can log and handle them properly.
    # The original broad except Exception was hiding real bugs.
