"""
core/auth.py — API key authentication
======================================
Single, consistent model: Redis-backed live billing keys.

How it works
------------
1. Google Apps Script (GAS) POSTs to /internal/register-key with
   { "api_key": "sk-safe-XXXXXXXXXX", "secret": GAS_WEBHOOK_SECRET }.
2. This module hashes the key and stores the hash in Redis with TTL.
3. Every ingest request calls verify_api_key() which checks Redis.

To switch to static .env mode (no Redis / no billing bridge):
- Set USE_REDIS_AUTH=false in .env
- Populate API_KEY_HASHES_JSON with pre-hashed keys
"""

import hashlib
import json
import os
from functools import lru_cache

import redis
from fastapi import Header, HTTPException, status

# ── Config ────────────────────────────────────────────────────────────────────
REDIS_URL        = os.getenv("REDIS_URL", "redis://localhost:6379/0")
API_KEY_SALT     = os.getenv("API_KEY_SALT", "")
USE_REDIS_AUTH   = os.getenv("USE_REDIS_AUTH", "true").lower() == "true"
STATIC_HASHES    = set(json.loads(os.getenv("API_KEY_HASHES_JSON", "[]")))
KEY_TTL_SECONDS  = 60 * 60 * 24 * 31  # 31 days max; GAS refreshes on payment


@lru_cache(maxsize=1)
def _redis_client() -> redis.Redis:
    return redis.from_url(REDIS_URL, decode_responses=True)


# ── Public API ────────────────────────────────────────────────────────────────

def hash_key(raw_key: str) -> str:
    """Return a salted SHA-256 hex digest of the API key."""
    return hashlib.sha256(f"{API_KEY_SALT}{raw_key}".encode()).hexdigest()


def register_key(raw_key: str, ttl: int = KEY_TTL_SECONDS) -> None:
    """Store a hashed key in Redis (called by /internal/register-key)."""
    digest = hash_key(raw_key)
    _redis_client().setex(f"apikey:{digest}", ttl, "1")


def revoke_key(raw_key: str) -> None:
    """Remove a key from Redis immediately."""
    digest = hash_key(raw_key)
    _redis_client().delete(f"apikey:{digest}")


def is_valid_key(raw_key: str) -> bool:
    """Return True if the key is currently valid."""
    if not raw_key:
        return False
    digest = hash_key(raw_key)
    if USE_REDIS_AUTH:
        return _redis_client().exists(f"apikey:{digest}") == 1
    # Static fallback
    return digest in STATIC_HASHES


# ── FastAPI dependency ────────────────────────────────────────────────────────

def require_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """FastAPI dependency — raise 401 if key is invalid."""
    if not is_valid_key(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key
