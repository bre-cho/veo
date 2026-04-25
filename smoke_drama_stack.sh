#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000/api/v1}"
TOKEN="${TOKEN:-}"
PROJECT_ID="${PROJECT_ID:-00000000-0000-0000-0000-000000000001}"
EPISODE_ID="${EPISODE_ID:-00000000-0000-0000-0000-000000000101}"
SCENE_ID="${SCENE_ID:-00000000-0000-0000-0000-000000000201}"

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

echo "[1/8] Create Authority character"
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

echo "[2/8] Create Rebel character"
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

echo "[3/8] Upsert relationship Authority -> Rebel"
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

echo "[4/8] Analyze scene"
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

echo "[5/8] Compile render bridge"
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

echo "[6/8] Persist via process endpoint"
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
  echo "process endpoint unavailable or contract differs; continuing read checks"
fi

echo "[6a/8] Assert power shifts persisted"
POWER_COUNT=$(json_get "/drama/scenes/${SCENE_ID}/power-shifts" | python -c 'import json,sys; print(len(json.load(sys.stdin)))')
test "$POWER_COUNT" -ge 1 || { echo "FAIL: expected >=1 DramaPowerShift, got ${POWER_COUNT}" >&2; exit 1; }
echo "  power shifts: ${POWER_COUNT}"

echo "[6b/8] Assert memory traces created"
MEMORY_COUNT=$(json_get "/drama/memory/characters/${AUTHORITY_ID}" | python -c 'import json,sys; print(len(json.load(sys.stdin)))')
test "$MEMORY_COUNT" -ge 1 || { echo "FAIL: expected >=1 memory trace, got ${MEMORY_COUNT}" >&2; exit 1; }
echo "  memory traces: ${MEMORY_COUNT}"

echo "[6c/8] Assert arc updated"
ARC_COUNT=$(json_get "/drama/arcs/${AUTHORITY_ID}" | python -c 'import json,sys; print(len(json.load(sys.stdin)))')
test "$ARC_COUNT" -ge 1 || { echo "FAIL: expected >=1 arc entry, got ${ARC_COUNT}" >&2; exit 1; }
echo "  arc entries: ${ARC_COUNT}"

echo "[7/8] Recall memory"
set +e
json_get "/drama/memory/characters/${REBEL_ID}/recall?trigger=authority_pressure&limit=5"
RECALL_STATUS=$?
set -e
if [[ "$RECALL_STATUS" -ne 0 ]]; then
  echo "memory recall returned no data yet; this is expected before first persisted worker run"
fi

echo "[8/8] Recompute episode continuity"
set +e
curl -fsS -X POST "${BASE_URL}/drama/admin/episodes/${EPISODE_ID}/recompute?starting_scene_id=${SCENE_ID}&scene_ids=${SCENE_ID}" \
  -H "Content-Type: application/json" \
  "${AUTH_HEADER[@]}"
RECOMPUTE_EPISODE_STATUS=$?
set -e
if [[ "$RECOMPUTE_EPISODE_STATUS" -ne 0 ]]; then
  echo "episode recompute endpoint unavailable or no persisted states yet"
fi

echo "DRAMA STACK SMOKE: COMPLETED"
