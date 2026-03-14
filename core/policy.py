from __future__ import annotations

from urllib.parse import urlparse
import urllib.robotparser

import redis

from core.config import get_settings
from core.logging import logger


settings = get_settings()


class CrawlBudgetService:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.ttl_seconds = 86400

    def check_and_increment(self, domain: str, limit: int) -> bool:
        key = f"crawl:{domain}"
        with self.redis.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(key)
                    current = pipe.get(key)
                    current_count = int(current) if current else 0
                    if current_count >= limit:
                        pipe.unwatch()
                        return False
                    pipe.multi()
                    pipe.incr(key, 1)
                    if current_count == 0:
                        pipe.expire(key, self.ttl_seconds)
                    pipe.execute()
                    return True
                except redis.WatchError:
                    continue


class PolicyEngine:
    def __init__(self, redis_client: redis.Redis):
        self.crawl_budget = CrawlBudgetService(redis_client)

    def check_robots(self, url: str, user_agent: str = "*") -> bool:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(robots_url)
        try:
            parser.read()
            return parser.can_fetch(user_agent, url)
        except Exception as exc:
            logger.warning("robots.check_failed", url=url, robots_url=robots_url, error=str(exc), security_event=True)
            allowed_by_robots = settings.robots_error_mode == "allow"
            if allowed_by_robots:
                logger.warning("robots.fail_open", url=url, mode="allow", security_event=True)
            return allowed_by_robots

    def check_budget(self, url: str, limit: int = 1000) -> bool:
        parsed = urlparse(url)
        return self.crawl_budget.check_and_increment(parsed.netloc, limit)
