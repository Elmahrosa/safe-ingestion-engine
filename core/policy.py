# core/policy.py
from __future__ import annotations
import fnmatch
import yaml
from dataclasses import dataclass
from urllib.parse import urlparse
from datetime import datetime

@dataclass
class PolicyDecision:
    allowed: bool
    status: str
    reason: str

class PolicyEngine:
    def __init__(self, path="policies/policy.yml"):
        with open(path, "r", encoding="utf-8") as f:
            self.policy = yaml.safe_load(f)

    def decide(self, url: str) -> PolicyDecision:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()

        defaults = self.policy.get("defaults", {})
        if defaults.get("block_weekends", False):
            if datetime.now().weekday() >= 5:
                return PolicyDecision(False, "BLOCKED_POLICY", "Policy: weekends blocked")

        for rule in self.policy.get("domains", []):
            pat = rule.get("match", "").lower()
            action = rule.get("action", "deny").lower()
            if fnmatch.fnmatch(host, pat):
                if action == "deny":
                    return PolicyDecision(False, "BLOCKED_POLICY", f"Policy deny: {pat} ({rule.get('note','')})")
                return PolicyDecision(True, "ALLOWED_POLICY", f"Policy allow: {pat} ({rule.get('note','')})")

        return PolicyDecision(True, "ALLOWED_POLICY", "Policy default allow (subject to robots/scope/budget)")
