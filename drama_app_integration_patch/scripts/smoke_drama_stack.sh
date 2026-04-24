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
AUTHORITY_ID=$(python - "$AUTHORITY" <<'PY'
import json
import sys
print(json.loads(sys.argv[1]).get("id", ""))
PY
)

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
REBEL_ID=$(python - "$REBEL" <<'PY'
import json
import sys
print(json.loads(sys.argv[1]).get("id", ""))
PY
)

if [[ -z "$AUTHORITY_ID" || -z "$REBEL_ID" ]]; then
  echo "Could not parse character IDs. Check router response contract." >&2
  exit 1
fi

echo "[3/8] Create relationship Authority -> Rebel"
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
ANALYSIS=$(json_post "/drama/scenes/analyze" "{
  \"project_id\": \"${PROJECT_ID}\",
  \"scene_id\": \"${SCENE_ID}\",
  \"character_ids\": [\"${AUTHORITY_ID}\", \"${REBEL_ID}\"],
  \"scene_context\": {
    \"scene_goal\": \"Authority tries to force confession while Rebel exposes a hidden truth\",
    \"visible_conflict\": \"discipline\",
    \"hidden_conflict\": \"control of narrative\",
    \"pressure_level\": 0.82,
    \"key_secret_in_play\": \"Authority already knew the betrayal\"
  }
}")
echo "$ANALYSIS"

echo "[5/8] Compile render bridge"
json_post "/drama/compile/scene" "{
  \"scene_context\": {
    \"project_id\": \"${PROJECT_ID}\",
    \"scene_id\": \"${SCENE_ID}\"
  },
  \"scene_analysis\": ${ANALYSIS},
  \"previous_scene_state\": null,
  \"character_arc_state\": null
}"

echo "[6/8] Persist via worker-compatible endpoint if available"
set +e
json_post "/drama/admin/recompute-scene" "{\"scene_id\": \"${SCENE_ID}\", \"project_id\": \"${PROJECT_ID}\"}"
RECOMPUTE_SCENE_STATUS=$?
set -e
if [[ "$RECOMPUTE_SCENE_STATUS" -ne 0 ]]; then
  echo "recompute-scene endpoint unavailable or contract differs; continuing read checks"
fi

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
json_post "/drama/admin/episodes/${EPISODE_ID}/recompute?starting_scene_id=${SCENE_ID}&scene_ids=${SCENE_ID}" "{}"
RECOMPUTE_EPISODE_STATUS=$?
set -e
if [[ "$RECOMPUTE_EPISODE_STATUS" -ne 0 ]]; then
  echo "episode recompute endpoint unavailable or no persisted states yet"
fi

echo "DRAMA STACK SMOKE: COMPLETED"
