import hashlib

from core.config import get_settings

def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

def is_valid_api_key(api_key: str) -> bool:
    settings = get_settings()
    return hash_api_key(api_key) in set(settings.api_key_hashes)
