#!/bin/bash
<<<<<<< HEAD

echo "=== Security Fixes Verification ==="
echo ""

echo "✅ Applied Files:"
echo "   - authentication/core_auth.py"
echo "   - api/routes_metrics.py" 
echo "   - scripts/rotate_api_keys.py"
echo ""

echo "📋 Manual Integration Status:"
echo ""

# Check if manual fixes have been applied
echo "1. PII stable_hash fix:"
if grep -q "hmac.new" $(find . -name "*.py" -exec grep -l "stable_hash" {} \; 2>/dev/null | head -1) 2>/dev/null; then
    echo "   ✅ HMAC implementation found"
else
    echo "   ❌ Still needs manual integration"
fi

echo ""
echo "2. Domain concurrency fix:"
if grep -q "pipe.watch" $(find . -name "*.py" -exec grep -l "DomainConcurrencyService" {} \; 2>/dev/null | head -1) 2>/dev/null; then
    echo "   ✅ Atomic Redis operations found"
else
    echo "   ❌ Still needs manual integration"
fi

echo ""
echo "3. Plan credits fix:"
if grep -q '"trial".*5' $(find . -name "*.py" -exec grep -l "PLAN_CREDITS" {} \; 2>/dev/null | head -1) 2>/dev/null; then
    echo "   ✅ Trial credits set to 5"
else
    echo "   ❌ Still needs manual integration"
fi

echo ""
echo "4. MCP ingest block fix:"
if grep -q "status.*upper" $(find . -name "*.py" -exec grep -l "ingest_url" {} \; 2>/dev/null | head -1) 2>/dev/null; then
    echo "   ✅ Status normalization found"
else
    echo "   ❌ Still needs manual integration"
fi

echo ""
echo "📖 See MANUAL_INTEGRATION_GUIDE.md for detailed instructions"
=======
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
>>>>>>> main
