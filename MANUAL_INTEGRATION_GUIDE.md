# Security Fixes - Manual Integration Guide

## Files Already Applied (Automatic)
✅ `authentication/core_auth.py` - HMAC + trial TTL fixes
✅ `api/routes_metrics.py` - Basic Auth guard for /metrics  
✅ `scripts/rotate_api_keys.py` - Redis key rotation

## Manual Integration Required

### 1. PII stable_hash Fix (Fix #01)
**Target File:** Find the file containing the `stable_hash()` function (likely in a PII/data processing module)
**Current Issue:** Using insecure MD5 hash
**Required Change:** Replace with HMAC-SHA256

```python
# REPLACE the existing stable_hash function with:
def stable_hash(value: str) -> str:
    return hmac.new(
        settings.pii_salt.encode("utf-8"),
        msg=value.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
```

**Import Requirements:** Ensure `import hmac` and `import hashlib` are present.

### 2. Domain Concurrency Fix (Fix #02)  
**Target File:** Find the `DomainConcurrencyService` class (likely in policy/rate limiting module)
**Current Issue:** Race condition in concurrent slot acquisition
**Required Change:** Replace entire class with atomic Redis operations

```python
# REPLACE the DomainConcurrencyService class with the version in:
# patched/policy_concurrency.snippet
```

Key improvements:
- Uses Redis WATCH/MULTI/EXEC for atomic acquisition
- Lua script for atomic decrement in release()
- Proper race condition handling

### 3. Plan Credits Configuration (Fix #05)
**Target File:** Find `PLAN_CREDITS` configuration (likely in settings/config module)
**Current Issue:** Trial plan has 1000 credits (too generous)
**Required Change:** Reduce trial credits to 5

```python
# REPLACE the PLAN_CREDITS dict with:
PLAN_CREDITS: dict[str, int] = {
    "trial":      5,       # 48-hour trial, 5 URL credits
    "starter":    500,     # $19/mo
    "growth":     5000,    # $49/mo
    "enterprise": 50000,   # custom
}
```

### 4. MCP Ingest Block Handling (Fix #09)
**Target File:** Find MCP ingest_url handler (likely in MCP server module)
**Current Issue:** Case-sensitive status comparison, missing BLOCKED status
**Required Change:** Add status normalization and BLOCKED handling

**Find the ingest_url handler and apply these changes:**
1. Add status normalization: `status = job["status"].upper()`
2. Add BLOCKED status handling:
```python
if status == "BLOCKED":
    return [types.TextContent(type="text", text=f"Blocked: {job.get('error_message')}")]
```

## Additional Manual Fixes (No Snippets Provided)

### Fix #04: SQLAlchemy Dashboard Query
**Target:** `dashboard/app.py`, tab1 functionality
**Issue:** SQL injection via string formatting
**Fix:** Use parameterized queries with SQLAlchemy

### Fix #06: HTTP Connector Redirects  
**Target:** `collectors/http_connector.py`
**Issue:** Global redirect following settings
**Fix:** Set `follow_redirects` explicitly per request call

### Fix #07: Queue Tasks Security Events
**Target:** `infrastructure/queue/tasks.py`
**Issue:** Overly broad security event logging
**Fix:** Only log security_event for SSRFBlockedError specifically

## Verification Steps
After applying all fixes:
1. Run security tests
2. Verify authentication endpoints
3. Test rate limiting
4. Check PII hashing consistency
5. Validate MCP status handling
