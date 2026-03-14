from __future__ import annotations

import hashlib
import hmac

from core.config import get_settings


def hash_api_key(api_key: str, salt: str | None = None) -> str:
    settings = get_settings()
    secret = (salt or settings.api_key_salt).encode("utf-8")
    return hmac.new(secret, api_key.encode("utf-8"), hashlib.sha256).hexdigest()


def is_valid_api_key(api_key: str) -> bool:
    settings = get_settings()
    return hmac.compare_digest(
        hash_api_key(api_key),
        next((h for h in settings.api_key_hashes if h == hash_api_key(api_key)), ""),
    )
