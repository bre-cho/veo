#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# run_tests.sh – single GO / NO-GO verdict for staging readiness
#
# Usage:
#   ./run_tests.sh           # full gate (requires Docker – postgres + redis)
#   ./run_tests.sh --local   # backend unit tests only (no Docker required)
#   ./run_tests.sh --ci      # alias for --local (used inside containers)
#
# E2E gate notes:
#   The E2E section is a HARD BLOCKER in the full gate.  It runs:
#     1. TypeScript compile (npx tsc --noEmit) – must pass
#     2. Playwright smoke specs tagged @smoke – must pass
#   The --local / --ci modes intentionally skip E2E (no browser available
#   in CI containers or local envs without Playwright installed).
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

# ── GROUP C: E2E browser execution gate (HARD BLOCKER) ────────────────────
# This is a browser execution gate, NOT just discovery.
# TypeScript errors and Playwright @smoke failures both cause a non-zero exit.
run_e2e_gate() {
  echo ""
  echo "══════════════════════════════════════════════════════"
  echo " E2E  TypeScript compile + Playwright @smoke  [BLOCKER]"
  echo "══════════════════════════════════════════════════════"
  cd "$ROOT_DIR/e2e"

  # Step 1: TypeScript compile – hard failure
  npx tsc -p tsconfig.json --noEmit || fail "E2E TypeScript compile failed – fix type errors before merging"

  # Step 2: Playwright smoke specs – hard failure
  # Use --grep to target specs tagged @smoke; pass --reporter=list for clean CI output.
  npx playwright test --grep "@smoke" --reporter=list \
    || fail "E2E Playwright smoke specs failed – fix failing specs before merging"

  ok "E2E gate passed"
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
    # NOTE: only backend tests are run here. Frontend build and E2E gate
    # are skipped intentionally (no Node/browser environment required).
    # Use the full gate (no flags) or scripts/verify_runtime.sh for a
    # complete staging check including browser execution.
    run_backend_tests
    ok "LOCAL GO/NO-GO: PASSED (backend only – run without flags for full gate)"
    ;;
  *)
    # Full gate: runtime stack + backend + frontend + e2e (hard blocker)
    run_runtime_gate
    run_frontend_build
    run_e2e_gate
    ok "FULL GO/NO-GO: PASSED – staging is GREEN"
    ;;
esac
