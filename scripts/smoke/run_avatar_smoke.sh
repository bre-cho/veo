#!/usr/bin/env bash
# run_avatar_smoke.sh — avatar pipeline smoke test runner
#
# Runs 5 checks in order:
#   1. decision  — avatar_id present in response
#   2. render    — avatar context carried into render
#   3. feedback good  — governance action for high-performing avatar
#   4. feedback bad   — governance action for low-performing avatar
#   5. scheduler local — cooldown/priority ranking without server
#
# Usage:
#   ./scripts/smoke/run_avatar_smoke.sh
#
# Override defaults:
#   BASE_URL=http://localhost:8000 \
#   DECISION_ENDPOINT=/api/v1/decision/test \
#   PROJECT_ID=22222222-2222-2222-2222-222222222222 \
#   FEEDBACK_ENDPOINT=/api/v1/feedback/test \
#   ./scripts/smoke/run_avatar_smoke.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BASE_URL="${BASE_URL:-http://localhost:8000}"
DECISION_ENDPOINT="${DECISION_ENDPOINT:-/api/v1/decision/test}"
PROJECT_ID="${PROJECT_ID:-22222222-2222-2222-2222-222222222222}"
RENDER_ENDPOINT="${RENDER_ENDPOINT:-/api/v1/projects/${PROJECT_ID}/render}"
FEEDBACK_ENDPOINT="${FEEDBACK_ENDPOINT:-/api/v1/feedback/test}"

PASS=0
FAIL=0

_ok()  { echo "  ✓  $1"; ((PASS++)); }
_fail(){ echo "  ✗  $1"; ((FAIL++)); }

_curl() {
    local label="$1"; local url="$2"; local payload_file="$3"; local check_key="$4"
    echo ""
    echo "── $label"
    echo "   POST $url"
    local http_code
    http_code=$(curl -s -o /tmp/_avatar_smoke_resp.json -w "%{http_code}" \
        -X POST "$url" \
        -H "Content-Type: application/json" \
        -d "@${payload_file}" 2>/dev/null || echo "000")
    if [[ "$http_code" == "000" ]]; then
        _fail "connection refused — is the server running at $BASE_URL?"
        return
    fi
    echo "   HTTP $http_code"
    if [[ "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
        if command -v jq &>/dev/null; then
            local value
            value=$(jq -r "${check_key} // \"null\"" /tmp/_avatar_smoke_resp.json 2>/dev/null || echo "parse_error")
            if [[ "$value" != "null" && "$value" != "" && "$value" != "parse_error" ]]; then
                _ok "$check_key = $value"
            else
                _fail "$check_key missing or null in response"
                jq . /tmp/_avatar_smoke_resp.json 2>/dev/null | head -30
            fi
        else
            # jq not available, basic grep check
            local raw_key
            raw_key=$(echo "$check_key" | sed 's/\.\([a-z_]*\)$/\1/')
            if grep -q "\"${raw_key}\"" /tmp/_avatar_smoke_resp.json 2>/dev/null; then
                _ok "$check_key found in response (install jq for deeper check)"
            else
                _fail "$check_key not found in response"
            fi
        fi
    else
        _fail "HTTP $http_code — endpoint may not exist yet"
        cat /tmp/_avatar_smoke_resp.json 2>/dev/null | head -20
    fi
}

echo "╔══════════════════════════════════════════════════════════╗"
echo "║          AVATAR PIPELINE SMOKE TEST                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo "  base_url = $BASE_URL"

# ── 1. Decision ───────────────────────────────────────────────
_curl \
    "1/5  DECISION — avatar_id present" \
    "${BASE_URL}${DECISION_ENDPOINT}" \
    "${SCRIPT_DIR}/decision_smoke.json" \
    ".avatar_id"

# ── 2. Render ─────────────────────────────────────────────────
_curl \
    "2/5  RENDER — avatar context carried" \
    "${BASE_URL}${RENDER_ENDPOINT}" \
    "${SCRIPT_DIR}/render_smoke.json" \
    ".avatar.avatar_id"

# ── 3. Feedback good ──────────────────────────────────────────
_curl \
    "3/5  FEEDBACK GOOD — avatar_governance present" \
    "${BASE_URL}${FEEDBACK_ENDPOINT}" \
    "${SCRIPT_DIR}/feedback_smoke_good.json" \
    ".avatar_governance"

# ── 4. Feedback bad ───────────────────────────────────────────
_curl \
    "4/5  FEEDBACK BAD — avatar_governance present" \
    "${BASE_URL}${FEEDBACK_ENDPOINT}" \
    "${SCRIPT_DIR}/feedback_smoke_bad.json" \
    ".avatar_governance"

# ── 5. Scheduler local ────────────────────────────────────────
echo ""
echo "── 5/5  SCHEDULER LOCAL — cooldown/priority ranking"
if python3 "${SCRIPT_DIR}/scheduler_smoke.py"; then
    _ok "scheduler cooldown guard"
else
    _fail "scheduler cooldown guard"
fi

# ── Summary ───────────────────────────────────────────────────
echo ""
echo "──────────────────────────────────────────────────────────"
echo "  PASS: $PASS   FAIL: $FAIL"
if [[ $FAIL -eq 0 ]]; then
    echo "  → GO — all 5 avatar smoke checks passed ✓"
    exit 0
else
    echo "  → NO-GO — $FAIL check(s) failed"
    exit 1
fi
