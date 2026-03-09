"""
core/policy.py — Policy engine: YAML rules + robots.txt + crawl budget.
Fixes:
  - evaluate() method was called everywhere but only decide() existed
  - No robots.txt integration despite being the primary policy entry point
  - No crawl-budget enforcement at runtime
"""

import logging
import os
import time
import warnings
from collections import defaultdict
from datetime import date
from typing import Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import yaml

logger = logging.getLogger(__name__)

POLICIES_DIR = os.getenv("POLICIES_DIR", "policies")
USER_AGENT   = os.getenv("USER_AGENT", "SafeSaaS/1.0")


class PolicyEngine:
    """
    Evaluates whether a URL may be fetched:
    1. YAML domain allow/deny rules
    2. robots.txt compliance
    3. Per-domain crawl-budget (in-memory, daily reset)
    """

    # Class-level shared state for crawl budgets across task invocations
    _crawl_counts: dict[str, int]   = defaultdict(int)
    _crawl_reset_date: date          = date.today()

    def __init__(self, policies_dir: str = POLICIES_DIR):
        self._rules = self._load_rules(policies_dir)

    # ── Rule loading ──────────────────────────────────────────────────────────

    def _load_rules(self, policies_dir: str) -> dict:
        rules: dict = {"domains": {}, "global": {}}
        rules_file = os.path.join(policies_dir, "rules.yaml")
        if not os.path.exists(rules_file):
            return rules
        try:
            with open(rules_file) as fh:
                data = yaml.safe_load(fh) or {}
            rules.update(data)
        except Exception as exc:
            logger.warning("Failed to load policy rules from %s: %s", rules_file, exc)
        return rules

    # ── robots.txt ────────────────────────────────────────────────────────────

    def _check_robots(self, url: str) -> tuple[bool, str]:
        """
        Returns (allowed: bool, reason: str).
        Fail-open on any exception (network timeout, malformed robots.txt).
        """
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            if rp.can_fetch(USER_AGENT, url):
                return True, "robots.txt allows"
            return False, f"Blocked by robots.txt at {robots_url}"
        except Exception as exc:
            # Fail-open: log a warning but don't block on transient errors
            logger.warning("robots.txt check failed for %s — failing open: %s", url, exc)
            return True, "robots.txt check failed (fail-open)"

    # ── Crawl budget ──────────────────────────────────────────────────────────

    def _check_crawl_budget(self, domain: str) -> tuple[bool, str]:
        today = date.today()
        if PolicyEngine._crawl_reset_date != today:
            PolicyEngine._crawl_counts.clear()
            PolicyEngine._crawl_reset_date = today

        domain_rules = self._rules.get("domains", {}).get(domain, {})
        budget = domain_rules.get(
            "crawl_budget",
            self._rules.get("global", {}).get("crawl_budget", 0),
        )

        if budget <= 0:
            return True, "No crawl budget set"

        PolicyEngine._crawl_counts[domain] += 1
        if PolicyEngine._crawl_counts[domain] > budget:
            return False, f"Crawl budget exceeded for {domain} (limit {budget}/day)"

        return True, f"Crawl budget ok ({PolicyEngine._crawl_counts[domain]}/{budget})"

    # ── YAML domain rules ─────────────────────────────────────────────────────

    def _check_yaml_rules(self, url: str, domain: str) -> tuple[bool, str]:
        domain_rules = self._rules.get("domains", {}).get(domain, {})
        if not domain_rules:
            return True, "No domain rule"

        action = domain_rules.get("action", "allow")
        if action == "deny":
            reason = domain_rules.get("reason", f"Domain {domain!r} is denied by policy")
            return False, reason

        # Path-based deny patterns
        for pattern in domain_rules.get("deny_paths", []):
            if pattern in url:
                return False, f"URL path matches deny pattern: {pattern!r}"

        return True, "YAML rules allow"

    # ── Public API ────────────────────────────────────────────────────────────

    def evaluate(self, url: str) -> dict:
        """
        Primary entry point. Returns:
        {"allowed": bool, "reason": str}
        Previously only decide() existed — renamed and extended here.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # 1. YAML rules
        yaml_ok, yaml_reason = self._check_yaml_rules(url, domain)
        if not yaml_ok:
            return {"allowed": False, "reason": yaml_reason}

        # 2. robots.txt
        robots_ok, robots_reason = self._check_robots(url)
        if not robots_ok:
            return {"allowed": False, "reason": robots_reason}

        # 3. Crawl budget
        budget_ok, budget_reason = self._check_crawl_budget(domain)
        if not budget_ok:
            return {"allowed": False, "reason": budget_reason}

        return {"allowed": True, "reason": "All checks passed"}

    def decide(self, url: str) -> dict:
        """Alias for evaluate() — kept for backwards compat."""
        return self.evaluate(url)
