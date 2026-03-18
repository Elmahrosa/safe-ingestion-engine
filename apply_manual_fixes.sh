#!/bin/bash

echo "=== Applying Manual Security Fixes ==="

# Create backup
BACKUP_DIR="backup_manual_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Fix 01: PII stable_hash - Apply to core/pii.py
echo "1. Applying PII stable_hash fix to core/pii.py..."
if [ -f "core/pii.py" ]; then
    cp "core/pii.py" "$BACKUP_DIR/"
    
    # Replace the stable_hash function
    python3 << 'PYTHON'
import re

# Read the current file
with open('core/pii.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define the new stable_hash function
new_function = '''def stable_hash(value: str) -> str:
    return hmac.new(
        settings.pii_salt.encode("utf-8"),
        msg=value.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()'''

# Replace the existing function (match the function definition and its body)
pattern = r'def stable_hash\(value: str\) -> str:.*?(?=\n\ndef|\n\nclass|\Z)'
content = re.sub(pattern, new_function, content, flags=re.DOTALL)

# Ensure imports are present
if 'import hmac' not in content:
    # Add import after other imports
    import_pattern = r'(import hashlib\n)'
    if 'import hashlib' in content:
        content = re.sub(import_pattern, r'\1import hmac\n', content)
    else:
        # Add both imports at the top
        content = 'import hashlib\nimport hmac\n' + content

# Write back
with open('core/pii.py', 'w', encoding='utf-8') as f:
    f.write(content)
PYTHON
    echo "   ✓ Applied HMAC stable_hash fix"
else
    echo "   ❌ core/pii.py not found"
fi

# Fix 02: Domain concurrency - Apply to core/policy.py
echo "2. Applying domain concurrency fix to core/policy.py..."
if [ -f "core/policy.py" ]; then
    cp "core/policy.py" "$BACKUP_DIR/"
    
    # Replace the DomainConcurrencyService class
    python3 << 'PYTHON'
import re

# Read the current file
with open('core/policy.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define the new class
new_class = '''class DomainConcurrencyService:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def acquire(self, domain: str, max_concurrent: int) -> bool:
        """Atomically acquire a concurrency slot. Race-free via WATCH/MULTI/EXEC."""
        key = f"concurrent:{domain}"
        with self.redis.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(key)
                    current = int(pipe.get(key) or 0)
                    if current >= max_concurrent:
                        pipe.unwatch()
                        return False
                    pipe.multi()
                    pipe.incr(key)
                    pipe.expire(key, 300)
                    pipe.execute()
                    return True
                except redis.WatchError:
                    continue

    def release(self, domain: str) -> None:
        """Decrement slot count, never below 0 (Lua for atomicity)."""
        key = f"concurrent:{domain}"
        lua = """
local v = tonumber(redis.call('get', KEYS[1]) or '0')
if v > 0 then redis.call('decr', KEYS[1]) end
"""
        self.redis.eval(lua, 1, key)'''

# Replace the existing class
pattern = r'class DomainConcurrencyService:.*?(?=\n\nclass|\n\ndef|\Z)'
content = re.sub(pattern, new_class, content, flags=re.DOTALL)

# Write back
with open('core/policy.py', 'w', encoding='utf-8') as f:
    f.write(content)
PYTHON
    echo "   ✓ Applied atomic domain concurrency fix"
else
    echo "   ❌ core/policy.py not found"
fi

# Fix 05: Plan credits - Apply to api/routes/ingest.py
echo "3. Applying plan credits fix to api/routes/ingest.py..."
if [ -f "api/routes/ingest.py" ]; then
    cp "api/routes/ingest.py" "$BACKUP_DIR/"
    
    # Update PLAN_CREDITS
    python3 << 'PYTHON'
import re

# Read the current file
with open('api/routes/ingest.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define the new PLAN_CREDITS
new_credits = '''PLAN_CREDITS: dict[str, int] = {
    "trial":      5,       # 48-hour trial, 5 URL credits
    "starter":    500,     # $19/mo
    "growth":     5000,    # $49/mo
    "enterprise": 50000,   # custom
}'''

# Replace the existing PLAN_CREDITS
pattern = r'PLAN_CREDITS: dict\[str, int\] = \{[^}]+\}'
content = re.sub(pattern, new_credits, content, flags=re.DOTALL)

# Write back
with open('api/routes/ingest.py', 'w', encoding='utf-8') as f:
    f.write(content)
PYTHON
    echo "   ✓ Applied trial credits limit (5 URLs)"
else
    echo "   ❌ api/routes/ingest.py not found"
fi

# Fix 09: MCP ingest block - Apply to mcp_server.py
echo "4. Applying MCP ingest block fix to mcp_server.py..."
if [ -f "mcp_server.py" ]; then
    cp "mcp_server.py" "$BACKUP_DIR/"
    
    # Replace the ingest_url handler
    python3 << 'PYTHON'
import re

# Read the current file
with open('mcp_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define the new handler block
new_handler = '''        if name == "ingest_url":
            url = arguments.get("url", "")
            if not url:
                return [types.TextContent(type="text", text="Error: url required")]
            payload = {"url": url}
            if k := arguments.get("idempotency_key"):
                payload["idempotency_key"] = k
            r = await client.post("/v1/ingest_async", json=payload)
            if r.status_code == 402:
                return [types.TextContent(type="text", text="No credits. Top up at https://safe.teosegypt.com")]
            if r.status_code != 200:
                return [types.TextContent(type="text", text=f"Error {r.status_code}: {r.text}")]
            job_id = r.json()["job_id"]
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                await asyncio.sleep(2)
                poll = await client.get(f"/v1/jobs/{job_id}")
                if poll.status_code != 200:
                    continue
                job = poll.json()
                status = job["status"].upper()          # normalise case
                if status == "COMPLETED":
                    return [types.TextContent(type="text", text=(
                        f"Ingestion complete | Job: {job_id} | PII redacted: {job.get('pii_found',0)}\n\n"
                        f"{job.get('result_excerpt','')}"
                    ))]
                if status == "BLOCKED":
                    return [types.TextContent(type="text", text=f"Blocked: {job.get('error_message')}")]
                if status == "FAILED":
                    return [types.TextContent(type="text", text=f"Failed: {job.get('error_message')}")]
                # PENDING / RUNNING / RETRYING — keep polling
            return [types.TextContent(type="text", text=f"Timeout. Poll manually: get_job(job_id='{job_id}')")]'''

# Find and replace the existing ingest_url handler
pattern = r'        if name == "ingest_url":.*?(?=\n        \w|\n\n|\Z)'
content = re.sub(pattern, new_handler, content, flags=re.DOTALL)

# Write back
with open('mcp_server.py', 'w', encoding='utf-8') as f:
    f.write(content)
PYTHON
    echo "   ✓ Applied MCP status normalization and BLOCKED handling"
else
    echo "   ❌ mcp_server.py not found"
fi

echo ""
echo "=== Additional manual fixes needed ==="
echo "📄 Fix 04: dashboard/app.py - SQL injection fix"
echo "📄 Fix 06: collectors/http_connector.py - redirect security fix"  
echo "📄 Fix 07: infrastructure/queue/tasks.py - security event specificity"

echo ""
echo "Backups stored in: $BACKUP_DIR/"
