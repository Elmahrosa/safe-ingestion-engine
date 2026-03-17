# fix_01_hmac_consistency.py
# ─────────────────────────────────────────────────────────────────────────────
# FINDING: Both core/pii.py and core/auth.py call hmac.new() correctly with
# positional digestmod.  Python's hmac.new(key, msg, digestmod) is valid.
# However the function is spelled `hmac.new` which is the correct stdlib name.
#
# ACTION: No functional change required.  Add explicit keyword argument for
# clarity and future-proofing (avoids confusion with the deprecated form).
#
# FILES AFFECTED: core/pii.py  core/auth.py
# ─────────────────────────────────────────────────────────────────────────────

# core/pii.py  — stable_hash()
# BEFORE:
#   return hmac.new(
#       settings.pii_salt.encode("utf-8"),
#       value.encode("utf-8"),
#       hashlib.sha256,
#   ).hexdigest()
#
# AFTER:
STABLE_HASH_PATCH = '''\
def stable_hash(value: str) -> str:
    return hmac.new(
        settings.pii_salt.encode("utf-8"),
        msg=value.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
'''

# core/auth.py  — hash_api_key()
# BEFORE:
#   return hmac.new(secret, api_key.encode("utf-8"), hashlib.sha256).hexdigest()
#
# AFTER:
HASH_API_KEY_PATCH = '''\
def hash_api_key(api_key: str, salt: str | None = None) -> str:
    settings = get_settings()
    secret = (salt or settings.api_key_salt).encode("utf-8")
    return hmac.new(
        secret,
        msg=api_key.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
'''

print("Fix 01: HMAC keyword-argument clarification patches printed above.")
print("Apply manually to core/pii.py and core/auth.py.")
