#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

echo "Preparing environment files..."
cp backend/.env.example backend/.env.dev || true
FRONTEND_ENV_FILE="${ROOT_DIR}/frontend/.env.local"
CREATED_FRONTEND_ENV_FILE=0
if [[ ! -f "${FRONTEND_ENV_FILE}" ]]; then
  touch "${FRONTEND_ENV_FILE}"
  CREATED_FRONTEND_ENV_FILE=1
fi
export BACKEND_SCHEMA_BOOTSTRAP="${BACKEND_SCHEMA_BOOTSTRAP:-metadata-create-all}"

cleanup() {
  echo "Tearing down runtime stack..."
  docker compose down -v || true
  if [[ "${CREATED_FRONTEND_ENV_FILE}" == "1" ]]; then
    rm -f "${FRONTEND_ENV_FILE}"
  fi
}
trap cleanup EXIT

echo "Starting runtime dependencies (postgres, redis, minio, api, workers)..."
docker compose up -d postgres redis minio minio-init api worker-render worker-audio worker-template worker-drama

echo "Waiting for API health..."
for _ in $(seq 1 80); do
  if curl -fsS http://localhost:8000/healthz >/dev/null; then
    break
  fi
  sleep 3
done
curl -fsS http://localhost:8000/healthz >/dev/null

echo "Running backend runtime verification in container..."
docker compose exec -T api bash -lc "
  cd /app &&
  python -m compileall app tests &&
  python -m pytest -q -m 'unit or integration or smoke'
"

echo "Runtime verification passed."
