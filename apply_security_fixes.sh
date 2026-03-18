#!/bin/bash

echo "=== Applying Security Fixes ==="
echo "Creating backup directory..."
mkdir -p backup_$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"

# Function to backup and replace file
backup_and_replace() {
    local source_file="$1"
    local target_file="$2"
    local description="$3"
    
    if [ -f "$target_file" ]; then
        echo "Backing up $target_file to $BACKUP_DIR/"
        cp "$target_file" "$BACKUP_DIR/"
    fi
    
    if [ -f "$source_file" ]; then
        echo "✓ Applying $description"
        cp "$source_file" "$target_file"
    else
        echo "✗ Source file $source_file not found"
    fi
}

echo ""
echo "=== Applying Complete File Replacements ==="

# Apply complete file replacements
backup_and_replace "patched/core_auth.py" "authentication/core_auth.py" "Fix 01+05: HMAC + trial TTL"
backup_and_replace "patched/api_routes_metrics.py" "api/routes_metrics.py" "Fix 03: /metrics Basic Auth"
backup_and_replace "patched/scripts_rotate_api_keys.py" "scripts/rotate_api_keys.py" "Fix 08: Redis key rotation"

echo ""
echo "=== Files requiring manual snippet integration ==="
echo "The following snippet files contain code that needs to be manually integrated:"
echo ""

if [ -f "patched/pii_stable_hash.snippet" ]; then
    echo "📄 Fix 01: PII stable_hash HMAC fix"
    echo "   File: patched/pii_stable_hash.snippet"
    echo "   Target: Find stable_hash() function and apply changes"
    echo ""
fi

if [ -f "patched/policy_concurrency.snippet" ]; then
    echo "📄 Fix 02: Domain concurrency atomic acquire"
    echo "   File: patched/policy_concurrency.snippet" 
    echo "   Target: DomainConcurrencyService class"
    echo ""
fi

if [ -f "patched/plan_credits.snippet" ]; then
    echo "📄 Fix 05: Plan credits trial limit"
    echo "   File: patched/plan_credits.snippet"
    echo "   Target: PLAN_CREDITS configuration"
    echo ""
fi

if [ -f "patched/mcp_ingest_block.snippet" ]; then
    echo "📄 Fix 09: MCP ingest block handling"
    echo "   File: patched/mcp_ingest_block.snippet"
    echo "   Target: MCP ingestion status handling"
    echo ""
fi

echo "=== Additional manual fixes needed ==="
echo "📄 Fix 04: dashboard/app.py - SQLAlchemy parameterized query in tab1"
echo "📄 Fix 06: collectors/http_connector.py - explicit follow_redirects per call" 
echo "📄 Fix 07: infrastructure/queue/tasks.py - security_event only for SSRFBlockedError"
echo ""
echo "Backups stored in: $BACKUP_DIR/"
