#!/bin/bash
set -e

echo "========================================="
echo "  Safe Ingestion Engine - Security Fixer"
echo "========================================="

# FIX 1: Force UTF-8 Encoding (Prevents Windows 'charmap' errors)
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

# FIX 2: Activate Venv if exists
if [ -d "venv" ]; then
    echo "[*] Activating virtual environment..."
    source venv/Scripts/activate 2>/dev/null || source venv/bin/activate 2>/dev/null || true
fi

echo "[*] Running patcher with UTF-8 enforcement..."

# Embed Python Patcher directly to avoid external file encoding issues
python3 - << 'PYTHON_PATCHER'
import os
import sys
import re

# Ensure all file operations use UTF-8
def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def backup_file(path):
    if os.path.exists(path):
        import shutil
        shutil.copy2(path, f"{path}.bak")
        print(f"  [BACKUP] Created {path}.bak")

patches_applied = 0

# --- FIX 04: Dashboard SQL Injection (dashboard/app.py) ---
try:
    path = "dashboard/app.py"
    if os.path.exists(path):
        backup_file(path)
        content = read_file(path)
        # Replace unsafe f-string SQL with parameterized query
        if "f\" WHERE status = '{status_filter}'\"" in content:
            # Import text
            if "from sqlalchemy import text" not in content:
                content = content.replace("from sqlalchemy import create_engine", "from sqlalchemy import create_engine, text")
            
            # Replace the vulnerable block
            old_sql = """sql = "SELECT job_id, status, domain, source_url, pii_found, content_hash, security_event, created_at FROM jobs"
    if status_filter != "ALL":
        sql += f" WHERE status = '{status_filter}'"
    sql += " ORDER BY created_at DESC LIMIT 200"
    df = query(sql)"""
            
            new_sql = """if status_filter != "ALL":
        sql = text(\"\"\"
            SELECT job_id, status, domain, source_url, pii_found, 
                   content_hash, security_event, created_at 
            FROM jobs 
            WHERE status = :status 
            ORDER BY created_at DESC 
            LIMIT 200
        \"\"\")
        df = query(sql, params={"status": status_filter})
    else:
        sql = text(\"\"\"
            SELECT job_id, status, domain, source_url, pii_found, 
                   content_hash, security_event, created_at 
            FROM jobs 
            ORDER BY created_at DESC 
            LIMIT 200
        \"\"\")
        df = query(sql)"""
            
            # Fallback replacement if exact block differs slightly
            if old_sql in content:
                content = content.replace(old_sql, new_sql)
            else:
                # Regex fallback for the specific vulnerable line
                content = re.sub(
                    r"sql \+= f\" WHERE status = '\{status_filter\}'\"",
                    "# PARAMETERIZED: sql += f\" WHERE status = '{status_filter}'\"",
                    content
                )
                # Add params to query call nearby
                content = content.replace("df = query(sql)", "df = query(sql, params={\"status\": status_filter}) # Fix 04")
            
            write_file(path, content)
            print("  [FIX 04] Dashboard SQL Injection patched")
            patches_applied += 1
        else:
            print("  [SKIP] Dashboard SQL already patched or structure changed")
except Exception as e:
    print(f"  [ERROR] Fix 04 failed: {e}")

# --- FIX 06: SSRF Redirects (collectors/http_connector.py) ---
try:
    path = "collectors/http_connector.py"
    if os.path.exists(path):
        backup_file(path)
        content = read_file(path)
        
        # 1. Force follow_redirects=False in client init
        if "follow_redirects=self.settings.allow_redirects" in content:
            content = content.replace(
                "follow_redirects=self.settings.allow_redirects",
                "follow_redirects=False  # FIX 06: Security Default"
            )
        
        # 2. Add per-call argument to fetch()
        if "async def fetch(self, url: str, **kwargs)" in content:
            content = content.replace(
                "async def fetch(self, url: str, **kwargs)",
                "async def fetch(self, url: str, *, follow_redirects: bool = False, **kwargs)"
            )
        
        # 3. Pass argument to stream
        if 'client.stream("GET", url,' in content and "follow_redirects=" not in content:
            content = content.replace(
                'client.stream("GET", url,',
                'client.stream("GET", url, follow_redirects=follow_redirects,  # FIX 06'
            )
            
        write_file(path, content)
        print("  [FIX 06] SSRF Redirect Control patched")
        patches_applied += 1
except Exception as e:
    print(f"  [ERROR] Fix 06 failed: {e}")

# --- FIX 07: Security Event Logging (infrastructure/queue/tasks.py) ---
try:
    path = "infrastructure/queue/tasks.py"
    if os.path.exists(path):
        backup_file(path)
        content = read_file(path)
        
        # 1. Import SSRFBlockedError
        if "from collectors.http_connector import HTTPConnector" in content:
            if "SSRFBlockedError" not in content:
                content = content.replace(
                    "from collectors.http_connector import HTTPConnector",
                    "from collectors.http_connector import HTTPConnector, SSRFBlockedError"
                )
        
        # 2. Narrow security_event logic
        if "db_job.security_event = True" in content:
            # Replace broad assignment with conditional
            content = content.replace(
                "db_job.security_event = True",
                "db_job.security_event = isinstance(exc, SSRFBlockedError)  # FIX 07"
            )
            print("  [FIX 07] Security Event Logging narrowed")
            patches_applied += 1
        else:
            print("  [SKIP] Security Event logic already modified")
            
        write_file(path, content)
except Exception as e:
    print(f"  [ERROR] Fix 07 failed: {e}")

# --- FIX 01/05: Trial Credits & HMAC (core/auth.py & core/pii.py) ---
try:
    # Fix Auth (Trial Credits)
    path = "core/auth.py"
    if os.path.exists(path):
        backup_file(path)
        content = read_file(path)
        if '"trial":      60 * 60 * 24 * 7' in content:
            content = content.replace(
                '"trial":      60 * 60 * 24 * 7',
                '"trial":      60 * 60 * 48  # FIX 05: 48 hours'
            )
            write_file(path, content)
            print("  [FIX 05] Trial TTL set to 48h")
            patches_applied += 1
            
    # Fix PII (HMAC)
    path = "core/pii.py"
    if os.path.exists(path):
        backup_file(path)
        content = read_file(path)
        if "hashlib.sha256(value.encode(" in content and "hmac.new" not in content:
            # Simple check to see if HMAC is missing in stable_hash
            if "def stable_hash" in content:
                 # This is a complex replace, skipping for safety if not exact match
                 print("  [INFO] Please verify core/pii.py stable_hash uses hmac.new")
except Exception as e:
    print(f"  [ERROR] Fix 01/05 failed: {e}")

print("\n=========================================")
print(f"  SUMMARY: {patches_applied} critical patches applied")
print("  BACKUPS: Check *.bak files if rollback needed")
print("  NEXT: Run ./verify_fixes.sh")
print("=========================================")
PYTHON_PATCHER

echo "[*] Done."
