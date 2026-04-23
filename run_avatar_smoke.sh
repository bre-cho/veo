#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
DECISION_ENDPOINT="${DECISION_ENDPOINT:-/api/v1/decision/test}"
RENDER_ENDPOINT="${RENDER_ENDPOINT:-/api/v1/projects/22222222-2222-2222-2222-222222222222/render}"
FEEDBACK_ENDPOINT="${FEEDBACK_ENDPOINT:-/api/v1/feedback/test}"
WORKDIR="$(cd "$(dirname "$0")" && pwd)"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1"; exit 1; }
}

need_cmd curl
need_cmd python3

HAS_JQ=1
if ! command -v jq >/dev/null 2>&1; then
  HAS_JQ=0
fi

echo "== Avatar Smoke Pack =="
echo "BASE_URL=$BASE_URL"
echo "DECISION_ENDPOINT=$DECISION_ENDPOINT"
echo "RENDER_ENDPOINT=$RENDER_ENDPOINT"
echo "FEEDBACK_ENDPOINT=$FEEDBACK_ENDPOINT"
echo

echo "[1/4] Decision smoke"
DECISION_RESP=$(curl -sS -X POST "$BASE_URL$DECISION_ENDPOINT" -H "Content-Type: application/json" --data @"$WORKDIR/decision_smoke.json")
if [ "$HAS_JQ" -eq 1 ]; then
  echo "$DECISION_RESP" | jq '{avatar_id, selection_mode: .avatar_selection.selection_mode, tournament_run_id: .avatar_selection.tournament_run_id}'
else
  echo "$DECISION_RESP"
fi

echo

echo "[2/4] Render smoke"
RENDER_RESP=$(curl -sS -X POST "$BASE_URL$RENDER_ENDPOINT" -H "Content-Type: application/json" --data @"$WORKDIR/render_smoke.json")
if [ "$HAS_JQ" -eq 1 ]; then
  echo "$RENDER_RESP" | jq '.avatar // {note:"render response does not echo avatar payload; inspect logs instead"}'
else
  echo "$RENDER_RESP"
fi

echo

echo "[3/4] Feedback smoke (good)"
GOOD_RESP=$(curl -sS -X POST "$BASE_URL$FEEDBACK_ENDPOINT" -H "Content-Type: application/json" --data @"$WORKDIR/feedback_smoke_good.json")
if [ "$HAS_JQ" -eq 1 ]; then
  echo "$GOOD_RESP" | jq '.avatar_governance // .'
else
  echo "$GOOD_RESP"
fi

echo

echo "[4/4] Feedback smoke (bad)"
BAD_RESP=$(curl -sS -X POST "$BASE_URL$FEEDBACK_ENDPOINT" -H "Content-Type: application/json" --data @"$WORKDIR/feedback_smoke_bad.json")
if [ "$HAS_JQ" -eq 1 ]; then
  echo "$BAD_RESP" | jq '.avatar_governance // .'
else
  echo "$BAD_RESP"
fi

echo

echo "[local] Scheduler smoke"
python3 "$WORKDIR/scheduler_smoke.py"

echo

echo "PASS: avatar smoke pack completed"
