# fix_05_trial_credits_sync.py
# ─────────────────────────────────────────────────────────────────────────────
# FINDING (MEDIUM): Three sources define trial credits and they disagree:
#
#   api/routes/ingest.py          PLAN_CREDITS["trial"] = 50
#   scripts/gas_billing_bridge.js PLANS.trial.credits   = 5
#   index.html                    "5 free URLs, 48h trial"
#   scripts/smoke_test.sh         asserts credits == 5
#
# Decision: Trial = 5 URLs, 48 hours.  This matches marketing copy and smoke test.
#
# FILES: api/routes/ingest.py · core/auth.py (PLAN_TTL) ·
#        scripts/gas_billing_bridge.js · index.html (already correct)
# ─────────────────────────────────────────────────────────────────────────────

# ── 1. api/routes/ingest.py — fix PLAN_CREDITS ───────────────────────────────
INGEST_PATCH = '''
PLAN_CREDITS: dict[str, int] = {
    "trial":      5,       # 48-hour trial, 5 URL credits  ← WAS 50
    "starter":    500,     # $29/mo
    "growth":     5000,    # $79/mo
    "enterprise": 50000,   # custom
}
'''

# ── 2. core/auth.py — trial TTL should be 48 h, not 7 days ──────────────────
AUTH_PATCH = '''
PLAN_TTL: dict[str, int] = {
    "trial":      60 * 60 * 48,   # 48 hours  ← WAS 7 days
    "starter":    60 * 60 * 24 * 32,
    "growth":     60 * 60 * 24 * 32,
    "enterprise": 60 * 60 * 24 * 32,
}
'''

# ── 3. scripts/gas_billing_bridge.js — already correct (credits: 5) ─────────
# No change needed in GAS script.

# ── 4. scripts/smoke_test.sh — already asserts credits == 5 ─────────────────
# No change needed in smoke test.

print("Fix 05:")
print("  api/routes/ingest.py  → PLAN_CREDITS['trial'] = 5  (was 50)")
print("  core/auth.py          → PLAN_TTL['trial'] = 48h    (was 7 days)")
print("  gas_billing_bridge.js → already correct (credits: 5)")
print("  index.html            → already correct ('5 free URLs, 48h trial')")
