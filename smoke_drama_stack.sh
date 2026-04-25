#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000/api/v1}"
TOKEN="${TOKEN:-}"
PROJECT_ID="${PROJECT_ID:-$(python -c 'import uuid; print(uuid.uuid4())')}"
EPISODE_ID="${EPISODE_ID:-$(python -c 'import uuid; print(uuid.uuid4())')}"
SCENE_ID="${SCENE_ID:-$(python -c 'import uuid; print(uuid.uuid4())')}"

AUTH_HEADER=()
if [[ -n "$TOKEN" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer $TOKEN")
fi

json_post() {
  local path="$1"
  local data="$2"
  curl -fsS "${BASE_URL}${path}" \
    -H "Content-Type: application/json" \
    "${AUTH_HEADER[@]}" \
    -d "$data"
}

json_get() {
  local path="$1"
  curl -fsS "${BASE_URL}${path}" \
    -H "Content-Type: application/json" \
    "${AUTH_HEADER[@]}"
}

echo "[1/11] Create Authority character"
AUTHORITY=$(json_post "/drama/characters" "{
  \"project_id\": \"${PROJECT_ID}\",
  \"name\": \"Director Vale\",
  \"archetype\": \"Authority\",
  \"outer_goal\": \"Force the rebel to confess\",
  \"hidden_need\": \"Protect control\",
  \"core_wound\": \"Being disrespected\",
  \"dominant_fear\": \"Losing the room\"
}")
echo "$AUTHORITY"
AUTHORITY_ID=$(python -c 'import json,sys; print(json.loads(sys.stdin.read()).get("id", ""))' <<<"$AUTHORITY")

echo "[2/11] Create Rebel character"
REBEL=$(json_post "/drama/characters" "{
  \"project_id\": \"${PROJECT_ID}\",
  \"name\": \"Mara\",
  \"archetype\": \"Rebel\",
  \"outer_goal\": \"Refuse the frame\",
  \"hidden_need\": \"Be seen as free\",
  \"core_wound\": \"Past control\",
  \"dominant_fear\": \"Submission\"
}")
echo "$REBEL"
REBEL_ID=$(python -c 'import json,sys; print(json.loads(sys.stdin.read()).get("id", ""))' <<<"$REBEL")

if [[ -z "$AUTHORITY_ID" || -z "$REBEL_ID" ]]; then
  echo "Could not parse character IDs. Check router response contract." >&2
  exit 1
fi

echo "[3/11] Upsert relationship Authority -> Rebel"
json_post "/drama/relationships" "{
  \"project_id\": \"${PROJECT_ID}\",
  \"source_character_id\": \"${AUTHORITY_ID}\",
  \"target_character_id\": \"${REBEL_ID}\",
  \"relation_type\": \"superior_rival\",
  \"trust_level\": 0.25,
  \"resentment_level\": 0.55,
  \"dominance_source_over_target\": 0.72,
  \"hidden_agenda_score\": 0.35,
  \"unresolved_tension_score\": 0.78
}"

echo "[4/11] Analyze scene"
ANALYZE_RESP=$(json_post "/drama/scenes/analyze" "{
  \"project_id\": \"${PROJECT_ID}\",
  \"scene_id\": \"${SCENE_ID}\",
  \"character_ids\": [\"${AUTHORITY_ID}\", \"${REBEL_ID}\"],
  \"scene_context\": {
    \"episode_id\": \"${EPISODE_ID}\",
    \"scene_goal\": \"Authority tries to force confession while Rebel exposes a hidden truth\",
    \"visible_conflict\": \"discipline\",
    \"hidden_conflict\": \"control of narrative\",
    \"pressure_level\": 0.82,
    \"key_secret_in_play\": \"Authority already knew the betrayal\"
  }
}")
echo "$ANALYZE_RESP"

echo "[5/11] Compile render bridge"
json_post "/drama/scenes/${SCENE_ID}/compile" "{
  \"project_id\": \"${PROJECT_ID}\",
  \"episode_id\": \"${EPISODE_ID}\",
  \"scene_context\": {
    \"scene_goal\": \"Authority tries to force confession while Rebel exposes a hidden truth\",
    \"visible_conflict\": \"discipline\",
    \"hidden_conflict\": \"control of narrative\",
    \"pressure_level\": 0.82
  },
  \"scene_analysis\": ${ANALYZE_RESP}
}"

echo "[5b/11] Assert blocking plan persisted"
BLOCKING_MODE=$(json_get "/drama/scenes/${SCENE_ID}/blocking" | python -c 'import json,sys; print(json.load(sys.stdin).get("spatial_mode",""))')
test -n "$BLOCKING_MODE" || { echo "FAIL: missing blocking spatial_mode" >&2; exit 1; }
echo "  blocking spatial_mode: ${BLOCKING_MODE}"

echo "[5c/11] Assert camera plan persisted"
CAMERA_MOVE=$(json_get "/drama/scenes/${SCENE_ID}/camera-plan" | python -c 'import json,sys; print(json.load(sys.stdin).get("primary_move",""))')
test -n "$CAMERA_MOVE" || { echo "FAIL: missing camera primary_move" >&2; exit 1; }
echo "  camera primary_move: ${CAMERA_MOVE}"

echo "[6/11] Persist via process endpoint"
set +e
json_post "/drama/admin/scenes/${SCENE_ID}/process" "{
  \"project_id\": \"${PROJECT_ID}\",
  \"character_ids\": [\"${AUTHORITY_ID}\", \"${REBEL_ID}\"],
  \"scene_context\": {
    \"episode_id\": \"${EPISODE_ID}\",
    \"scene_goal\": \"Authority tries to force confession while Rebel exposes a hidden truth\",
    \"visible_conflict\": \"discipline\",
    \"hidden_conflict\": \"control of narrative\",
    \"pressure_level\": 0.82,
    \"key_secret_in_play\": \"Authority already knew the betrayal\"
  },
  \"async_mode\": false
}"
RECOMPUTE_SCENE_STATUS=$?
set -e
if [[ "$RECOMPUTE_SCENE_STATUS" -ne 0 ]]; then
  echo "FAIL: process endpoint failed" >&2
  exit 1
fi

echo "[6b/11] Assert blocking plan present after /process"
BLOCKING_MODE_POST=$(json_get "/drama/scenes/${SCENE_ID}/blocking" | python -c 'import json,sys; print(json.load(sys.stdin).get("spatial_mode",""))')
test -n "$BLOCKING_MODE_POST" || { echo "FAIL: blocking spatial_mode missing after /process" >&2; exit 1; }
echo "  blocking spatial_mode post-process: ${BLOCKING_MODE_POST}"

echo "[6c/11] Assert camera plan present after /process"
CAMERA_MOVE_POST=$(json_get "/drama/scenes/${SCENE_ID}/camera-plan" | python -c 'import json,sys; print(json.load(sys.stdin).get("primary_move",""))')
test -n "$CAMERA_MOVE_POST" || { echo "FAIL: camera primary_move missing after /process" >&2; exit 1; }
echo "  camera primary_move post-process: ${CAMERA_MOVE_POST}"

echo "[7/11] Assert power shifts persisted"
POWER_COUNT=$(json_get "/drama/scenes/${SCENE_ID}/power-shifts" | python -c 'import json,sys; print(len(json.load(sys.stdin)))')
test "$POWER_COUNT" -ge 1 || { echo "FAIL: expected >=1 DramaPowerShift, got ${POWER_COUNT}" >&2; exit 1; }
echo "  power shifts: ${POWER_COUNT}"

echo "[8/11] Assert memory traces created"
MEMORY_COUNT=$(json_get "/drama/memory/characters/${AUTHORITY_ID}" | python -c 'import json,sys; print(len(json.load(sys.stdin)))')
test "$MEMORY_COUNT" -ge 1 || { echo "FAIL: expected >=1 memory trace, got ${MEMORY_COUNT}" >&2; exit 1; }
echo "  memory traces: ${MEMORY_COUNT}"

echo "[9/11] Assert arc updated"
ARC_COUNT=$(json_get "/drama/arcs/${AUTHORITY_ID}" | python -c 'import json,sys; print(len(json.load(sys.stdin)))')
test "$ARC_COUNT" -ge 1 || { echo "FAIL: expected >=1 arc entry, got ${ARC_COUNT}" >&2; exit 1; }
echo "  arc entries: ${ARC_COUNT}"

echo "[10/11] Recall memory"
RECALL_COUNT=$(json_get "/drama/memory/characters/${AUTHORITY_ID}/recall?trigger=discipline&limit=5" | python -c 'import json,sys; print(len(json.load(sys.stdin)))')
test "$RECALL_COUNT" -ge 1 || { echo "FAIL: expected recalled memory, got ${RECALL_COUNT}" >&2; exit 1; }
echo "  recalled memories: ${RECALL_COUNT}"

echo "[11/11] Recompute episode continuity"
set +e
curl -fsS -X POST "${BASE_URL}/drama/admin/episodes/${EPISODE_ID}/recompute?starting_scene_id=${SCENE_ID}&scene_ids=${SCENE_ID}" \
  -H "Content-Type: application/json" \
  "${AUTH_HEADER[@]}"
RECOMPUTE_EPISODE_STATUS=$?
set -e
if [[ "$RECOMPUTE_EPISODE_STATUS" -ne 0 ]]; then
  echo "FAIL: episode recompute failed" >&2
  exit 1
fi

echo "DRAMA STACK SMOKE: COMPLETED"
