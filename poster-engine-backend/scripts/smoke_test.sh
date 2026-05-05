#!/usr/bin/env bash
set -euo pipefail
BASE=${BASE:-http://localhost:8000}
curl -fsS "$BASE/health"
echo
BRAND=$(curl -fsS -X POST "$BASE/api/v1/brands" -H 'Content-Type: application/json' -d '{"name":"Luxury Beauty Demo"}')
echo "$BRAND"
BRAND_ID=$(python -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<< "$BRAND")
PROJECT=$(curl -fsS -X POST "$BASE/api/v1/projects" -H 'Content-Type: application/json' -d "{\"brand_id\":\"$BRAND_ID\",\"product_name\":\"Luxury Red Lipstick\"}")
echo "$PROJECT"
PROJECT_ID=$(python -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<< "$PROJECT")
curl -fsS -X POST "$BASE/api/v1/projects/$PROJECT_ID/generate"
echo
curl -fsS "$BASE/api/v1/projects/$PROJECT_ID/variants"
echo
