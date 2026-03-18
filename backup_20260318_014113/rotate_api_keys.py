#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone

from sqlalchemy import select

from core.auth import hash_api_key
from core.database import session_scope
from core.models import Job


def rotate_key(job_id: str, new_key: str) -> str:
    hashed = hash_api_key(new_key)
    with session_scope() as session:
        job = session.scalar(select(Job).where(Job.job_id == job_id))
        if job:
            job.api_key_hash = hashed
            job.updated_at = datetime.now(timezone.utc)
            return hashed
    raise ValueError(f"Job {job_id} not found")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--new-key", required=True)
    args = parser.parse_args()

    result = rotate_key(args.job_id, args.new_key)
    print(f"Key rotated for {args.job_id}. Hash: {result[:16]}...")
