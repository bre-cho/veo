#!/usr/bin/env bash
set -euo pipefail

echo "=============================================================="
echo "FULL CODE AUDIT - FINDING ALL ERRORS"
echo "=============================================================="
echo ""

mkdir -p audit_results
RESULTS_DIR="audit_results/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo "Results will be saved to: $RESULTS_DIR"
echo ""

run_and_log() {
  local log_file="$1"
  shift
  if "$@" > "$log_file" 2>&1; then
    return 0
  fi
  return 1
}

is_service_up() {
  local service="$1"
  docker compose ps --status running "$service" 2>/dev/null | grep -q "$service"
}

ensure_stack() {
  if is_service_up "api"; then
    return 0
  fi

  echo "Bringing up compose stack for container-based checks..."
  BACKEND_SCHEMA_BOOTSTRAP=metadata-create-all \
    docker compose up -d postgres redis minio minio-init api worker beat flower frontend edge-relay \
    > "$RESULTS_DIR/00_compose_up.log" 2>&1 || {
      echo "FAIL: Could not start compose stack"
      echo "See: $RESULTS_DIR/00_compose_up.log"
      return 1
    }
}

echo "--------------------------------------------------------------"
echo "1) PYTHON SYNTAX CHECK"
echo "--------------------------------------------------------------"
echo ""

echo "Compiling all Python files..."
if run_and_log "$RESULTS_DIR/01_syntax_check.log" python -m compileall backend/app backend/scripts -q; then
  echo "PASS: Python syntax"
else
  echo "FAIL: Python syntax"
  echo "See: $RESULTS_DIR/01_syntax_check.log"
  cat "$RESULTS_DIR/01_syntax_check.log"
fi
echo ""

echo "Checking each file individually..."
find backend -name "*.py" -type f | while IFS= read -r file; do
  python -m py_compile "$file" 2>&1 | tee -a "$RESULTS_DIR/01_individual_errors.log" >/dev/null
done
echo ""

ensure_stack

echo "--------------------------------------------------------------"
echo "2) IMPORT CHECK"
echo "--------------------------------------------------------------"
echo ""

echo "Checking imports in API container..."
if docker compose exec -T api sh -c '
cd /app
python << "EOF"
import os
import sys

sys.path.insert(0, "/app")

errors = []
success = []

for root, dirs, files in os.walk("/app/app"):
    for file in files:
        if file.endswith(".py") and not file.startswith("__"):
            filepath = os.path.join(root, file)
            rel_path = filepath.replace("/app/", "")
            try:
                module_path = rel_path.replace("/", ".").replace(".py", "")
                __import__(module_path)
                success.append(rel_path)
                print(f"PASS {rel_path}")
            except Exception as e:
                errors.append((rel_path, str(e)))
                print(f"FAIL {rel_path}: {e}")

print("=" * 70)
print(f"PASS count: {len(success)}")
print(f"FAIL count: {len(errors)}")
print("=" * 70)

if errors:
    print("\\nERRORS FOUND:")
    for path, error in errors:
        print(f"\\nFile: {path}")
        print(f"Error: {error}")
    raise SystemExit(1)
EOF
' > "$RESULTS_DIR/02_import_check.log" 2>&1; then
  echo "PASS: Imports"
else
  echo "FAIL: Imports"
  echo "See: $RESULTS_DIR/02_import_check.log"
fi
echo ""

echo "--------------------------------------------------------------"
echo "3) CODE QUALITY CHECK"
echo "--------------------------------------------------------------"
echo ""

echo "Running flake8 critical checks..."
if docker compose exec -T api sh -c 'pip install -q flake8 && flake8 /app/app --count --select=E9,F63,F7,F82 --show-source --statistics' \
  > "$RESULTS_DIR/03_flake8.log" 2>&1; then
  echo "PASS: Flake8 critical errors"
else
  echo "WARN: Flake8 found issues"
  echo "See: $RESULTS_DIR/03_flake8.log"
  head -30 "$RESULTS_DIR/03_flake8.log" || true
fi
echo ""

echo "--------------------------------------------------------------"
echo "4) RUNNING TESTS"
echo "--------------------------------------------------------------"
echo ""

echo "Installing pytest in API container..."
docker compose exec -T api pip install -q pytest pytest-asyncio > "$RESULTS_DIR/04_pytest_install.log" 2>&1 || true

echo "Running backend tests..."
if docker compose exec -T api python -m pytest /app/tests -v --tb=short --maxfail=5 > "$RESULTS_DIR/04_pytest.log" 2>&1; then
  echo "PASS: Tests"
else
  echo "FAIL: Tests"
  echo "See: $RESULTS_DIR/04_pytest.log"
  echo "Test summary tail:"
  tail -50 "$RESULTS_DIR/04_pytest.log" || true
fi
echo ""

echo "--------------------------------------------------------------"
echo "5) FRONTEND CHECK"
echo "--------------------------------------------------------------"
echo ""

if [ -d "frontend" ]; then
  echo "Checking package-lock.json..."
  if docker compose run --rm --no-deps frontend sh -lc 'cd /app && npm ci --dry-run' > "$RESULTS_DIR/05_npm_ci.log" 2>&1; then
    echo "PASS: package-lock.json"
  else
    echo "FAIL: package-lock.json"
    echo "See: $RESULTS_DIR/05_npm_ci.log"
  fi

  echo ""
  echo "Building frontend in one-off container..."
  if docker compose run --rm --no-deps frontend sh -lc 'cd /app && npm ci && npm run build' > "$RESULTS_DIR/05_npm_build.log" 2>&1; then
    echo "PASS: Frontend build"
  else
    echo "FAIL: Frontend build"
    echo "See: $RESULTS_DIR/05_npm_build.log"
  fi
fi
echo ""

echo "--------------------------------------------------------------"
echo "6) DATABASE MIGRATIONS"
echo "--------------------------------------------------------------"
echo ""

echo "Checking Alembic migrations..."
if docker compose exec -T api sh -c 'cd /app && alembic upgrade head' > "$RESULTS_DIR/06_alembic.log" 2>&1; then
  echo "PASS: Alembic migrations"
else
  echo "FAIL: Alembic migrations"
  echo "See: $RESULTS_DIR/06_alembic.log"
fi
echo ""

echo "--------------------------------------------------------------"
echo "7) API HEALTH CHECK"
echo "--------------------------------------------------------------"
echo ""

echo "Checking API health with retry..."
if curl --retry 20 --retry-all-errors --retry-delay 1 -fsS http://localhost:8000/healthz > "$RESULTS_DIR/07_health.log" 2>&1; then
  echo "PASS: API health"
  cat "$RESULTS_DIR/07_health.log"
else
  echo "FAIL: API health"
  echo "See: $RESULTS_DIR/07_health.log"
fi
echo ""

echo "--------------------------------------------------------------"
echo "8) CIRCULAR IMPORT CHECK"
echo "--------------------------------------------------------------"
echo ""

docker compose exec -T api sh -c 'pip install -q pydeps && pydeps /app/app --max-bacon=2 -o /tmp/deps.svg' \
  > "$RESULTS_DIR/08_circular_raw.log" 2>&1 || true

grep -Ein '\\b(cycle|circular)\\b' "$RESULTS_DIR/08_circular_raw.log" > "$RESULTS_DIR/08_circular.log" || true

if [ -s "$RESULTS_DIR/08_circular.log" ]; then
  echo "WARN: Potential circular imports found"
  cat "$RESULTS_DIR/08_circular.log"
else
  echo "PASS: No obvious circular imports"
fi
echo ""

echo "--------------------------------------------------------------"
echo "AUDIT SUMMARY"
echo "--------------------------------------------------------------"
echo ""

{
  echo "# Code Audit Summary"
  echo "Generated: $(date)"
  echo ""
  echo "## Results"
  echo ""
} > "$RESULTS_DIR/SUMMARY.md"

for log in "$RESULTS_DIR"/*.log; do
  name="$(basename "$log" .log)"
  if [ "$name" = "08_circular_raw" ]; then
    continue
  fi

  # Count only real error signals, not summary counters like "FAIL count: 0".
  errors="$(
    {
      grep -Eiv '^FAIL count:[[:space:]]*[0-9]+$' "$log" 2>/dev/null \
        | grep -Eic '(^FAIL[[:space:]]|^ERROR:?|Traceback|Exception|\bF821\b|\bE9\b|\bF63\b|\bF7\b|\bF82\b)'
    } || true
  )"
  [ -n "$errors" ] || errors=0
  echo "- $name: $errors potential issues" | tee -a "$RESULTS_DIR/SUMMARY.md"
done

echo ""
echo "Full results: $RESULTS_DIR"
echo "Summary: $RESULTS_DIR/SUMMARY.md"
echo ""
echo "=============================================================="