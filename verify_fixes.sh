#!/bin/bash

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
