from __future__ import annotations

import hashlib
import hmac

import redis as redis_lib

from core.config import get_settings

_redis_client: redis_lib.Redis | None = None


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
    return hmac.new(secret, api_key.encode("utf-8"), hashlib.sha256).hexdigest()


def register_api_key(api_key: str, credits: int = 100, plan: str = "starter") -> str:
    """Store a newly issued API key in Redis and return its hash preview-safe value."""
    key_hash = hash_api_key(api_key)
    r = _get_redis()
    r.hset("api_keys", key_hash, credits)
    r.hset("api_meta", key_hash, plan)
    return key_hash


def is_valid_api_key(api_key: str) -> bool:
    key_hash = hash_api_key(api_key)
    return _get_redis().hexists("api_keys", key_hash)


def get_credits(api_key: str) -> int:
    key_hash = hash_api_key(api_key)
    value = _get_redis().hget("api_keys", key_hash)
    return int(value) if value is not None else 0


def deduct_credit(api_key: str) -> bool:
    """Atomically deduct one credit. Returns False when no credits remain."""
    key_hash = hash_api_key(api_key)
    redis_client = _get_redis()
    bucket = "api_keys"

    with redis_client.pipeline() as pipe:
        while True:
            try:
                pipe.watch(bucket)
                current = redis_client.hget(bucket, key_hash)
                credits = int(current) if current is not None else 0
                if credits <= 0:
                    pipe.unwatch()
                    return False
                pipe.multi()
                pipe.hincrby(bucket, key_hash, -1)
                pipe.execute()
                return True
            except redis_lib.WatchError:
                continue


def add_credits(api_key: str, amount: int) -> int:
    key_hash = hash_api_key(api_key)
    return int(_get_redis().hincrby("api_keys", key_hash, amount))


def get_key_info(api_key: str) -> dict:
    key_hash = hash_api_key(api_key)
    redis_client = _get_redis()
    credits = redis_client.hget("api_keys", key_hash)
    plan = redis_client.hget("api_meta", key_hash)
    return {
        "valid": credits is not None,
        "credits": int(credits) if credits is not None else 0,
        "plan": plan or "unknown",
        "hash_preview": key_hash[:12],
    }
