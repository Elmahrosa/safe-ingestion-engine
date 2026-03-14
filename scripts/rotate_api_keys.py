#!/usr/bin/env python3
"""
scripts/rotate_api_keys.py
==========================
Rotate API keys in Redis without downtime.

Usage
-----
# Dry run — show what would be rotated
python scripts/rotate_api_keys.py --dry-run

# Rotate keys for a specific user email
python scripts/rotate_api_keys.py --email user@example.com

# Rotate all keys expiring within N days
python scripts/rotate_api_keys.py --expiring-within 7

# Revoke a specific key immediately
python scripts/rotate_api_keys.py --revoke sk-safe-XXXXXXXXXX

Environment
-----------
Reads REDIS_URL and API_KEY_SALT from .env (or environment).
"""

import argparse
import os
import sys
from pathlib import Path

# Load .env if present
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import redis

REDIS_URL    = os.getenv("REDIS_URL", "redis://localhost:6379/0")
API_KEY_SALT = os.getenv("API_KEY_SALT", "")

_r = redis.from_url(REDIS_URL, decode_responses=True)


def _hash(key: str) -> str:
    import hashlib
    return hashlib.sha256(f"{API_KEY_SALT}{key}".encode()).hexdigest()


def list_all_keys() -> list[str]:
    return _r.keys("apikey:*")


def revoke(raw_key: str, dry: bool = False) -> None:
    digest  = _hash(raw_key)
    redis_k = f"apikey:{digest}"
    if dry:
        print(f"[DRY] Would delete {redis_k}")
        return
    deleted = _r.delete(redis_k)
    if deleted:
        print(f"✅  Revoked  {redis_k}")
    else:
        print(f"⚠   Not found: {redis_k}")


def rotate(raw_key: str, new_key: str, ttl_days: int = 31, dry: bool = False) -> None:
    """Revoke old key, register new key."""
    revoke(raw_key, dry=dry)
    new_digest  = _hash(new_key)
    redis_k     = f"apikey:{new_digest}"
    if dry:
        print(f"[DRY] Would register {redis_k} TTL={ttl_days}d")
        return
    _r.setex(redis_k, ttl_days * 86400, "1")
    print(f"✅  Registered {redis_k} (TTL {ttl_days} days)")


def show_expiring(within_days: int = 7) -> None:
    threshold = within_days * 86400
    keys = list_all_keys()
    print(f"Keys expiring within {within_days} days ({len(keys)} total in Redis):")
    for k in keys:
        ttl = _r.ttl(k)
        if 0 < ttl <= threshold:
            print(f"  {k}  TTL={ttl}s  ({ttl//86400}d {(ttl%86400)//3600}h)")


def main() -> None:
    p = argparse.ArgumentParser(description="Safe Ingestion Engine — API key rotation tool")
    p.add_argument("--dry-run",          action="store_true", help="Preview without making changes")
    p.add_argument("--revoke",           metavar="KEY",       help="Revoke a specific key")
    p.add_argument("--expiring-within",  metavar="DAYS", type=int, default=None,
                   help="List keys expiring within N days")
    p.add_argument("--list",             action="store_true", help="List all Redis key hashes")
    args = p.parse_args()

    try:
        _r.ping()
    except Exception as e:
        print(f"❌  Cannot connect to Redis: {e}")
        sys.exit(1)

    if args.list:
        keys = list_all_keys()
        print(f"{len(keys)} keys in Redis:")
        for k in keys:
            ttl = _r.ttl(k)
            print(f"  {k}  TTL={ttl}s")

    elif args.revoke:
        revoke(args.revoke, dry=args.dry_run)

    elif args.expiring_within is not None:
        show_expiring(args.expiring_within)

    else:
        p.print_help()


if __name__ == "__main__":
    main()
