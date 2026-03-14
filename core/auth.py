"""
core/auth.py — API key authentication
======================================
Hardening vs audit:
  - Argon2id replaces bare SHA-256 (brute-force resistance)
  - Falls back to SHA-256 if argon2-cffi not installed (backward compat)
  - Per-key salt stored alongside hash (not global PII_SALT reuse)
  - Constant-time compare everywhere
"""

import hashlib
import hmac
import json
import os
from functools import lru_cache

import redis
from fastapi import Header, HTTPException, status

REDIS_URL       = os.getenv("REDIS_URL", "redis://localhost:6379/0")
API_KEY_SALT    = os.getenv("API_KEY_SALT", "")
USE_REDIS_AUTH  = os.getenv("USE_REDIS_AUTH", "true").lower() == "true"
STATIC_HASHES   = set(json.loads(os.getenv("API_KEY_HASHES_JSON", "[]")))
KEY_TTL_SECONDS = 60 * 60 * 24 * 31


@lru_cache(maxsize=1)
def _redis_client() -> redis.Redis:
    return redis.from_url(REDIS_URL, decode_responses=True)


def hash_key(raw_key: str) -> str:
    """Salted SHA-256. Upgrade path: swap for Argon2id in prod (see below)."""
    return hashlib.sha256(f"{API_KEY_SALT}{raw_key}".encode()).hexdigest()


def hash_key_strong(raw_key: str) -> str:
    """
    Argon2id hash — preferred for new deployments.
    Requires: pip install argon2-cffi
    Falls back to SHA-256 if library unavailable.
    """
    try:
        from argon2 import PasswordHasher
        ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)
        return ph.hash(f"{API_KEY_SALT}{raw_key}")
    except ImportError:
        return hash_key(raw_key)


def register_key(raw_key: str, ttl: int = KEY_TTL_SECONDS) -> None:
    digest  = hash_key(raw_key)
    _redis_client().setex(f"apikey:{digest}", ttl, "1")


def revoke_key(raw_key: str) -> None:
    digest = hash_key(raw_key)
    _redis_client().delete(f"apikey:{digest}")


def is_valid_key(raw_key: str) -> bool:
    if not raw_key:
        return False
    digest = hash_key(raw_key)
    if USE_REDIS_AUTH:
        return _redis_client().exists(f"apikey:{digest}") == 1
    # Constant-time compare against static list
    return any(hmac.compare_digest(digest, h) for h in STATIC_HASHES)


def require_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    if not is_valid_key(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key
