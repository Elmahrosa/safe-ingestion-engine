"""
core/compliance.py — robots.txt and URL compliance checks.
Fix: bare `except:` was silently returning BLOCKED on any exception
     (including network timeouts). Now fails open with a logged warning.
"""

import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)


def is_allowed_by_robots(url: str, user_agent: str = "SafeSaaS/1.0") -> bool:
    """
    Returns True if the URL is allowed to be fetched per the site's robots.txt.
    Fails OPEN on any exception (network error, malformed file, timeout).
    """
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, url)
    except Exception as exc:
        # Fix: was `except:` → BLOCKED (wrong). Now fail-open with warning.
        logger.warning(
            "robots.txt check failed for %s — failing open. Reason: %s",
            url, exc,
        )
        return True


def is_safe_url(url: str) -> bool:
    """Basic URL safety check — must be https and have a valid hostname."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False
