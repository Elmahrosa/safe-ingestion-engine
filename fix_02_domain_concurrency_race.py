# fix_02_domain_concurrency_race.py
# ─────────────────────────────────────────────────────────────────────────────
# FINDING (HIGH): DomainConcurrencyService.acquire() does a non-atomic
# GET then INCR.  Under concurrent load the check races and max_concurrent
# can be exceeded.
#
# FILE: core/policy.py  — class DomainConcurrencyService
# ─────────────────────────────────────────────────────────────────────────────

# ── REPLACE the entire DomainConcurrencyService class with this ──────────────

PATCH = '''
class DomainConcurrencyService:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def acquire(self, domain: str, max_concurrent: int) -> bool:
        """
        Atomically acquire a concurrency slot for *domain*.
        Uses WATCH/MULTI/EXEC so the check-then-increment is race-free.
        Returns True if slot acquired, False if at max_concurrent.
        """
        key = f"concurrent:{domain}"
        with self.redis.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(key)
                    current = int(pipe.get(key) or 0)
                    if current >= max_concurrent:
                        pipe.unwatch()
                        return False
                    pipe.multi()
                    pipe.incr(key)
                    pipe.expire(key, 300)
                    pipe.execute()
                    return True
                except redis.WatchError:
                    continue  # retry on concurrent modification

    def release(self, domain: str) -> None:
        key = f"concurrent:{domain}"
        # Lua script ensures we never go below 0
        lua = """
local v = tonumber(redis.call('get', KEYS[1]) or '0')
if v > 0 then
    redis.call('decr', KEYS[1])
end
"""
        self.redis.eval(lua, 1, key)
'''

print("Fix 02: Replace DomainConcurrencyService in core/policy.py with the")
print("PATCH string above.")
