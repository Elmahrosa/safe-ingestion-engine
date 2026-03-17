# fix_08_rotate_api_keys.py
# ─────────────────────────────────────────────────────────────────────────────
# FINDING (LOW): scripts/rotate_api_keys.py updates job.api_key_hash in the
# database, which re-binds *jobs* to a new owner.  That's wrong.
# Key rotation means: register new key in Redis with same credits/plan,
# then expire the old key.  Job history should stay associated with the
# original key hash for audit integrity.
#
# FILE: scripts/rotate_api_keys.py  — full replacement
# ─────────────────────────────────────────────────────────────────────────────

REPLACEMENT = '''#!/usr/bin/env python3
"""
rotate_api_keys.py — rotate an API key in Redis without touching job history.

Usage:
    python scripts/rotate_api_keys.py --old-key sk-abc123 --new-key sk-xyz789

What it does:
    1. Reads the current credit balance and plan for --old-key from Redis
    2. Registers --new-key in Redis with the same credits, plan, and remaining TTL
    3. Revokes --old-key (hard delete from Redis)
    4. Prints a confirmation

Job records in the database are intentionally left unchanged — they remain
associated with the original key hash for audit trail integrity.
"""
from __future__ import annotations

import argparse
import sys

from core.auth import get_key_info, register_api_key, revoke_api_key, _get_redis, hash_api_key, _credit_key, _meta_key


def rotate(old_key: str, new_key: str) -> None:
    info = get_key_info(old_key)
    if not info["valid"]:
        print(f"ERROR: old key is invalid or already expired.", file=sys.stderr)
        sys.exit(1)

    credits   = info["credits"]
    plan      = info["plan"]
    ttl_left  = info["expires_in_seconds"]   # None = no expiry

    # Register new key
    new_hash = register_api_key(
        new_key,
        credits=credits,
        plan=plan,
        ttl_seconds=ttl_left,
    )

    # Revoke old key
    revoke_api_key(old_key)

    print(f"Rotated successfully.")
    print(f"  Old key hash : {hash_api_key(old_key)[:16]}... (revoked)")
    print(f"  New key hash : {new_hash[:16]}...")
    print(f"  Plan         : {plan}")
    print(f"  Credits       : {credits}")
    print(f"  TTL remaining : {ttl_left}s" if ttl_left else "  TTL remaining : no expiry")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rotate an API key in Redis.")
    parser.add_argument("--old-key", required=True, help="Current API key to retire")
    parser.add_argument("--new-key", required=True, help="New API key to activate")
    args = parser.parse_args()
    rotate(args.old_key, args.new_key)
'''

print("Fix 08: Replace scripts/rotate_api_keys.py entirely with REPLACEMENT above.")
print("The new script rotates keys in Redis only; job history is preserved for auditing.")
