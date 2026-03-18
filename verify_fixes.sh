#!/bin/bash
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

echo "========================================="
echo "  Verifying Security Fixes"
echo "========================================="

# Check Fix 04 (SQLI)
if grep -q "params=" dashboard/app.py 2>/dev/null; then
    echo "[PASS] Fix 04: Dashboard uses parameterized queries"
else
    echo "[FAIL] Fix 04: Dashboard still vulnerable to SQL Injection"
fi

# Check Fix 06 (SSRF)
if grep -q "follow_redirects=False" collectors/http_connector.py 2>/dev/null; then
    echo "[PASS] Fix 06: HTTP Connector defaults to no redirects"
else
    echo "[FAIL] Fix 06: HTTP Connector may follow redirects"
fi

# Check Fix 07 (Security Event)
if grep -q "isinstance.*SSRFBlockedError" infrastructure/queue/tasks.py 2>/dev/null; then
    echo "[PASS] Fix 07: Security events limited to SSRF blocks"
else
    echo "[FAIL] Fix 07: Security events may be over-reported"
fi

# Check Fix 05 (Trial TTL)
if grep -q "60 \* 60 \* 48" core/auth.py 2>/dev/null; then
    echo "[PASS] Fix 05: Trial TTL set to 48 hours"
else
    echo "[WARN] Fix 05: Trial TTL might still be 7 days"
fi

echo "========================================="
