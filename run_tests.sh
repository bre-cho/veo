#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[1/3] Backend tests"
cd "$ROOT_DIR/backend"
pytest -q

echo "[2/3] Frontend build"
cd "$ROOT_DIR/frontend"
npm run build

echo "[3/3] E2E typecheck + spec discovery"
cd "$ROOT_DIR/e2e"
npx tsc -p tsconfig.json --noEmit
npx playwright test --list

echo "All checks passed."
