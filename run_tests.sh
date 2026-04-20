#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# run_tests.sh – single GO / NO-GO verdict for staging readiness
#
# Usage:
#   ./run_tests.sh           # full gate (requires Docker – postgres + redis)
#   ./run_tests.sh --local   # backend unit tests only (no Docker required)
#   ./run_tests.sh --ci      # alias for --local (used inside containers)
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODE="${1:-}"

# ── helpers ────────────────────────────────────────────────────────────────
fail() { echo "❌  $*" >&2; exit 1; }
ok()   { echo "✅  $*"; }

# ── GROUP A: backend tests ─────────────────────────────────────────────────
run_backend_tests() {
  echo ""
  echo "══════════════════════════════════════════"
  echo " BACKEND  unit / integration / smoke tests"
  echo "══════════════════════════════════════════"
  cd "$ROOT_DIR/backend"
  python -m compileall app tests -q
  python -m pytest -q -m "unit or integration or smoke"
  ok "Backend tests passed"
}

# ── GROUP B: frontend build ────────────────────────────────────────────────
run_frontend_build() {
  echo ""
  echo "═══════════════════════════════"
  echo " FRONTEND  type-check + build  "
  echo "═══════════════════════════════"
  cd "$ROOT_DIR/frontend"
  npm run build
  ok "Frontend build passed"
}

# ── GROUP C: E2E smoke discovery (non-blocking) ────────────────────────────
run_e2e_discovery() {
  echo ""
  echo "══════════════════════════════════════"
  echo " E2E  typecheck + spec discovery only  "
  echo "══════════════════════════════════════"
  cd "$ROOT_DIR/e2e"
  npx tsc -p tsconfig.json --noEmit || { echo "⚠️  E2E typecheck failed (non-blocking)"; return 0; }
  npx playwright test --list   || { echo "⚠️  Playwright list failed (non-blocking)"; return 0; }
  ok "E2E discovery passed"
}

# ── runtime stack gate (Docker) ────────────────────────────────────────────
run_runtime_gate() {
  echo ""
  echo "═══════════════════════════════════════════════════════"
  echo " RUNTIME GATE  (delegates to scripts/verify_runtime.sh)"
  echo "═══════════════════════════════════════════════════════"
  bash "$ROOT_DIR/scripts/verify_runtime.sh"
  ok "Runtime gate passed"
}

# ── dispatch ──────────────────────────────────────────────────────────────
case "$MODE" in
  --local|--ci)
    # Inside container or local dev without Docker.
    # NOTE: only backend tests are run here. Frontend build and E2E discovery
    # are skipped intentionally (no Node environment required). Use the full
    # gate (no flags) or scripts/verify_runtime.sh for a complete staging check.
    run_backend_tests
    ok "LOCAL GO/NO-GO: PASSED (backend only – run without flags for full gate)"
    ;;
  *)
    # Full gate: runtime stack + backend + frontend + e2e discovery
    run_runtime_gate
    run_frontend_build
    run_e2e_discovery
    ok "FULL GO/NO-GO: PASSED – staging is GREEN"
    ;;
esac
