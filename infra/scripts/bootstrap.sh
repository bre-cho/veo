#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${BACKEND_DIR:-${SCRIPT_DIR}/../../backend}"

echo "=== Bootstrap: Running Alembic migrations ==="
cd "${BACKEND_DIR}"
alembic upgrade head

echo ""
echo "=== Bootstrap: Running seed data ==="
bash "${SCRIPT_DIR}/seed.sh"

echo ""
echo "=== Bootstrap complete ==="
