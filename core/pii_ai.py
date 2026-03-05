# core/pii_ai.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

@dataclass
class AIPiiResult:
    entities: List[Dict[str, Any]]  # [{"type":"EMAIL","score":0.85,"start":10,"end":30}, ...]
    available: bool
    error: Optional[str] = None

def detect_pii_ai(text: str) -> AIPiiResult:
    """
    Uses Presidio if available. If not installed, returns available=False.
    """
    try:
        from presidio_analyzer import AnalyzerEngine
        analyzer = AnalyzerEngine()
        results = analyzer.analyze(text=text, language="en")
        ents = [
            {"type": r.entity_type, "score": float(r.score), "start": int(r.start), "end": int(r.end)}
            for r in results
        ]
        return AIPiiResult(entities=ents, available=True)
    except Exception as e:
        return AIPiiResult(entities=[], available=False, error=f"{type(e).__name__}: {e}")
