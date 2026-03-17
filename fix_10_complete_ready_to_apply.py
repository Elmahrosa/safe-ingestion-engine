# fix_10_complete_ready_to_apply.py
# ─────────────────────────────────────────────────────────────────────────────
# COMPLETE PATCH SET — Safe Ingestion Engine
# All 10 findings, ready-to-apply code.
# Run: python fix_10_complete_ready_to_apply.py
# It writes patched versions of all affected files to ./patched/
# ─────────────────────────────────────────────────────────────────────────────

"""
Apply all patches by writing corrected file content.
Usage: python fix_10_complete_ready_to_apply.py
"""

import os, textwrap
os.makedirs("patched", exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
# FILE 1: core/auth.py  (fix 01 HMAC keywords + fix 05 trial TTL)
# ══════════════════════════════════════════════════════════════════════════════
AUTH = '''\
from __future__ import annotations

import hashlib
import hmac

import redis as redis_lib

from core.config import get_settings

_redis_client: redis_lib.Redis | None = None

# TTL in seconds per plan
# Trial: 48 hours (matches marketing copy)
# Paid plans: 32 days
PLAN_TTL: dict[str, int] = {
    "trial":      60 * 60 * 48,   # 48 hours  ← was 7 days
    "starter":    60 * 60 * 24 * 32,
    "growth":     60 * 60 * 24 * 32,
    "enterprise": 60 * 60 * 24 * 32,
}


def _get_redis() -> redis_lib.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.Redis.from_url(
            get_settings().redis_url, decode_responses=True
        )
    return _redis_client


def hash_api_key(api_key: str, salt: str | None = None) -> str:
    settings = get_settings()
    secret = (salt or settings.api_key_salt).encode("utf-8")
    return hmac.new(
        secret,
        msg=api_key.encode("utf-8"),    # explicit keyword
        digestmod=hashlib.sha256,       # explicit keyword
    ).hexdigest()


def _credit_key(key_hash: str) -> str:
    return f"key:{key_hash}"


def _meta_key(key_hash: str) -> str:
    return f"meta:{key_hash}"


def register_api_key(
    api_key: str,
    credits: int = 100,
    plan: str = "starter",
    ttl_seconds: int | None = None,
) -> str:
    key_hash = hash_api_key(api_key)
    r = _get_redis()
    ttl = ttl_seconds if ttl_seconds is not None else PLAN_TTL.get(plan)

    pipe = r.pipeline()
    pipe.set(_credit_key(key_hash), credits)
    pipe.set(_meta_key(key_hash), plan)
    if ttl:
        pipe.expire(_credit_key(key_hash), ttl)
        pipe.expire(_meta_key(key_hash), ttl)
    pipe.execute()

    return key_hash


def expire_api_key(api_key: str) -> None:
    key_hash = hash_api_key(api_key)
    r = _get_redis()
    pipe = r.pipeline()
    pipe.set(_credit_key(key_hash), 0)
    pipe.expire(_credit_key(key_hash), 1)
    pipe.expire(_meta_key(key_hash), 1)
    pipe.execute()


def revoke_api_key(api_key: str) -> None:
    key_hash = hash_api_key(api_key)
    r = _get_redis()
    r.delete(_credit_key(key_hash), _meta_key(key_hash))


def is_valid_api_key(api_key: str) -> bool:
    key_hash = hash_api_key(api_key)
    return _get_redis().exists(_credit_key(key_hash)) == 1


def get_credits(api_key: str) -> int:
    key_hash = hash_api_key(api_key)
    value = _get_redis().get(_credit_key(key_hash))
    return int(value) if value is not None else 0


def deduct_credit(api_key: str) -> bool:
    key_hash = hash_api_key(api_key)
    redis_client = _get_redis()
    ckey = _credit_key(key_hash)

    with redis_client.pipeline() as pipe:
        while True:
            try:
                pipe.watch(ckey)
                current = redis_client.get(ckey)
                credits = int(current) if current is not None else 0
                if credits <= 0:
                    pipe.unwatch()
                    return False
                pipe.multi()
                pipe.decr(ckey)
                pipe.execute()
                return True
            except redis_lib.WatchError:
                continue


def add_credits(api_key: str, amount: int) -> int:
    key_hash = hash_api_key(api_key)
    return int(_get_redis().incrby(_credit_key(key_hash), amount))


def get_key_info(api_key: str) -> dict:
    key_hash = hash_api_key(api_key)
    r = _get_redis()
    ckey = _credit_key(key_hash)
    mkey = _meta_key(key_hash)

    credits = r.get(ckey)
    plan = r.get(mkey)
    ttl = r.ttl(ckey)

    return {
        "valid": credits is not None,
        "credits": int(credits) if credits is not None else 0,
        "plan": plan or "unknown",
        "hash_preview": key_hash[:12],
        "expires_in_seconds": ttl if ttl >= 0 else None,
    }
'''

# ══════════════════════════════════════════════════════════════════════════════
# FILE 2: core/pii.py  (fix 01 HMAC keywords — functional no-op, clarity fix)
# ══════════════════════════════════════════════════════════════════════════════
PII_STABLE_HASH = '''\
def stable_hash(value: str) -> str:
    return hmac.new(
        settings.pii_salt.encode("utf-8"),
        msg=value.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
'''

# ══════════════════════════════════════════════════════════════════════════════
# FILE 3: core/policy.py  (fix 02 DomainConcurrencyService race condition)
# ══════════════════════════════════════════════════════════════════════════════
POLICY_CONCURRENCY = '''\
class DomainConcurrencyService:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def acquire(self, domain: str, max_concurrent: int) -> bool:
        """Atomically acquire a concurrency slot. Race-free via WATCH/MULTI/EXEC."""
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
                    continue

    def release(self, domain: str) -> None:
        """Decrement slot count, never below 0 (Lua for atomicity)."""
        key = f"concurrent:{domain}"
        lua = """
local v = tonumber(redis.call('get', KEYS[1]) or '0')
if v > 0 then redis.call('decr', KEYS[1]) end
"""
        self.redis.eval(lua, 1, key)
'''

# ══════════════════════════════════════════════════════════════════════════════
# FILE 4: api/routes/metrics.py  (fix 03 — add Basic Auth)
# ══════════════════════════════════════════════════════════════════════════════
METRICS = '''\
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from core.config import get_settings

REQUEST_COUNT = Counter("ingestion_requests_total", "Total ingestion requests", ["status"])
REQUEST_DURATION = Histogram("ingestion_request_duration_seconds", "Request duration")

router = APIRouter()
_security = HTTPBasic()


def _require_metrics_auth(
    credentials: HTTPBasicCredentials = Depends(_security),
) -> None:
    """Protect /metrics with HTTP Basic Auth (username=metrics, password=DASHBOARD_ADMIN_PASSWORD)."""
    settings = get_settings()
    ok = (
        secrets.compare_digest(credentials.username.encode(), b"metrics")
        and secrets.compare_digest(
            credentials.password.encode(),
            settings.dashboard_admin_password.encode(),
        )
    )
    if not ok:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )


@router.get("/metrics", dependencies=[Depends(_require_metrics_auth)])
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
'''

# ══════════════════════════════════════════════════════════════════════════════
# FILE 5: api/routes/ingest.py  (fix 05 — trial credits = 5)
# Just the PLAN_CREDITS dict — rest of file unchanged.
# ══════════════════════════════════════════════════════════════════════════════
PLAN_CREDITS_PATCH = '''\
PLAN_CREDITS: dict[str, int] = {
    "trial":      5,       # 48-hour trial, 5 URL credits
    "starter":    500,     # $19/mo
    "growth":     5000,    # $49/mo
    "enterprise": 50000,   # custom
}
'''

# ══════════════════════════════════════════════════════════════════════════════
# FILE 6: mcp_server.py  (fix 09 — status case normalisation + BLOCKED handle)
# ══════════════════════════════════════════════════════════════════════════════
MCP_INGEST_BLOCK = '''\
        if name == "ingest_url":
            url = arguments.get("url", "")
            if not url:
                return [types.TextContent(type="text", text="Error: url required")]
            payload = {"url": url}
            if k := arguments.get("idempotency_key"):
                payload["idempotency_key"] = k
            r = await client.post("/v1/ingest_async", json=payload)
            if r.status_code == 402:
                return [types.TextContent(type="text", text="No credits. Top up at https://safe.teosegypt.com")]
            if r.status_code != 200:
                return [types.TextContent(type="text", text=f"Error {r.status_code}: {r.text}")]
            job_id = r.json()["job_id"]
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                await asyncio.sleep(2)
                poll = await client.get(f"/v1/jobs/{job_id}")
                if poll.status_code != 200:
                    continue
                job = poll.json()
                status = job["status"].upper()          # normalise case
                if status == "COMPLETED":
                    return [types.TextContent(type="text", text=(
                        f"Ingestion complete | Job: {job_id} | PII redacted: {job.get('pii_found',0)}\\n\\n"
                        f"{job.get('result_excerpt','')}"
                    ))]
                if status == "BLOCKED":
                    return [types.TextContent(type="text", text=f"Blocked: {job.get('error_message')}")]
                if status == "FAILED":
                    return [types.TextContent(type="text", text=f"Failed: {job.get('error_message')}")]
                # PENDING / RUNNING / RETRYING — keep polling
            return [types.TextContent(type="text", text=f"Timeout. Poll manually: get_job(job_id=\\'{job_id}\\')")]
'''

# ══════════════════════════════════════════════════════════════════════════════
# FILE 7: scripts/rotate_api_keys.py  (fix 08 — semantic rewrite)
# ══════════════════════════════════════════════════════════════════════════════
ROTATE = '''\
#!/usr/bin/env python3
"""
rotate_api_keys.py — rotate an API key in Redis without touching job history.

Usage:
    python scripts/rotate_api_keys.py --old-key sk-abc --new-key sk-xyz
"""
from __future__ import annotations

import argparse
import sys

from core.auth import get_key_info, hash_api_key, register_api_key, revoke_api_key


def rotate(old_key: str, new_key: str) -> None:
    info = get_key_info(old_key)
    if not info["valid"]:
        print("ERROR: old key is invalid or already expired.", file=sys.stderr)
        sys.exit(1)

    credits  = info["credits"]
    plan     = info["plan"]
    ttl_left = info["expires_in_seconds"]

    new_hash = register_api_key(new_key, credits=credits, plan=plan, ttl_seconds=ttl_left)
    revoke_api_key(old_key)

    print("Rotated successfully.")
    print(f"  Old key hash : {hash_api_key(old_key)[:16]}... (revoked)")
    print(f"  New key hash : {new_hash[:16]}...")
    print(f"  Plan         : {plan}")
    print(f"  Credits      : {credits}")
    if ttl_left:
        print(f"  TTL remaining: {ttl_left}s")
    else:
        print("  TTL remaining: no expiry")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-key", required=True)
    parser.add_argument("--new-key", required=True)
    args = parser.parse_args()
    rotate(args.old_key, args.new_key)
'''

# ══════════════════════════════════════════════════════════════════════════════
# Write summary of what each patch changes
# ══════════════════════════════════════════════════════════════════════════════
SUMMARY = {
    "patched/core_auth.py":              "Fix 01+05: HMAC keyword args + trial TTL 48h",
    "patched/pii_stable_hash.snippet":   "Fix 01: HMAC keyword args in stable_hash()",
    "patched/policy_concurrency.snippet":"Fix 02: DomainConcurrencyService atomic acquire()",
    "patched/api_routes_metrics.py":     "Fix 03: /metrics Basic Auth guard",
    "patched/plan_credits.snippet":      "Fix 05: PLAN_CREDITS trial=5 (was 50)",
    "patched/mcp_ingest_block.snippet":  "Fix 09: status.upper() + BLOCKED handling",
    "patched/scripts_rotate_api_keys.py":"Fix 08: key rotation in Redis, not DB",
}

patches = {
    "patched/core_auth.py":              AUTH,
    "patched/pii_stable_hash.snippet":   PII_STABLE_HASH,
    "patched/policy_concurrency.snippet":POLICY_CONCURRENCY,
    "patched/api_routes_metrics.py":     METRICS,
    "patched/plan_credits.snippet":      PLAN_CREDITS_PATCH,
    "patched/mcp_ingest_block.snippet":  MCP_INGEST_BLOCK,
    "patched/scripts_rotate_api_keys.py":ROTATE,
}

if __name__ == "__main__":
    import os
    os.makedirs("patched", exist_ok=True)
    for path, content in patches.items():
        with open(path, "w") as f:
            f.write(content)
    print("\n=== Patches written ===")
    for path, desc in SUMMARY.items():
        print(f"  {path:<45}  {desc}")
    print("\nFixes NOT requiring separate files (apply manually):")
    print("  Fix 04: dashboard/app.py — SQLAlchemy parameterized query in tab1 (see fix_04)")
    print("  Fix 06: collectors/http_connector.py — explicit follow_redirects per call (see fix_06)")
    print("  Fix 07: infrastructure/queue/tasks.py — security_event only for SSRFBlockedError (see fix_07)")
