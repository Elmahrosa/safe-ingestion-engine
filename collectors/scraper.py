import requests
from ratelimit import limits, sleep_and_retry

class SafeScraper:

    def __init__(self, guard, user_agent):
        self.guard = guard
        self.headers = {"User-Agent": user_agent}

    @sleep_and_retry
    @limits(calls=1, period=2)
    def fetch(self, url):

        r = requests.get(url, headers=self.headers, timeout=10)
        r.raise_for_status()

        return r.text, r.headers.get("Content-Type","unknown")
