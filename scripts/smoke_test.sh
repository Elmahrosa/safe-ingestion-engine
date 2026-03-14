#!/usr/bin/env bash
# scripts/smoke_test.sh
# =====================
# Quick smoke test against a running Safe Ingestion Engine API.
# Usage:
#   ./scripts/smoke_test.sh                          # localhost:8000
#   ./scripts/smoke_test.sh https://safe.teosegypt.com
#   API_KEY=sk-safe-XXXXXXXXXX ./scripts/smoke_test.sh

set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"
API_KEY="${API_KEY:-sk-safe-TESTKEY000}"
PASS=0
FAIL=0

green() { echo -e "\033[32m✅  $*\033[0m"; }
red()   { echo -e "\033[31m❌  $*\033[0m"; }
bold()  { echo -e "\033[1m$*\033[0m"; }

check() {
    local label="$1"
    local code="$2"
    local expected="$3"
    if [ "$code" -eq "$expected" ]; then
        green "$label (HTTP $code)"
        ((PASS++)) || true
    else
        red "$label — expected HTTP $expected, got $code"
        ((FAIL++)) || true
    fi
}

bold "▶  Smoke testing $BASE_URL"
echo ""

# 1. Health
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")
check "GET /health" "$CODE" 200

# 2. Metrics
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/metrics")
check "GET /metrics" "$CODE" 200

# 3. Status
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/v1/status")
check "GET /v1/status" "$CODE" 200

# 4. Ingest — no key → 422 or 401
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/v1/ingest" \
    -H "Content-Type: application/json" \
    -d '{"url":"https://example.com"}')
check "POST /v1/ingest (no key → 4xx)" "$CODE" 422

# 5. Ingest — bad key → 401
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/v1/ingest" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: sk-safe-BADKEY0000" \
    -d '{"url":"https://example.com"}')
check "POST /v1/ingest (bad key → 401)" "$CODE" 401

# 6. Ingest — valid key (only if key was registered in Redis)
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/v1/ingest" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d '{"url":"https://example.com","scrub_pii":true}')
if [ "$CODE" -eq 200 ]; then
    green "POST /v1/ingest (valid key → 200)"
    ((PASS++)) || true
elif [ "$CODE" -eq 401 ]; then
    echo -e "\033[33m⚠   POST /v1/ingest → 401 (key not in Redis — register it first)\033[0m"
else
    red "POST /v1/ingest — unexpected HTTP $CODE"
    ((FAIL++)) || true
fi

# 7. Docs reachable
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/docs")
check "GET /docs" "$CODE" 200

echo ""
bold "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
