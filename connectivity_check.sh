#!/usr/bin/env bash
set -u
BASE_URL="${1:-http://localhost:3000}"
AUTH_TOKEN="${AUTH_TOKEN:-}"

echo "== Frontend -> Backend API map =="
echo "POST /api/orchestrator/stream  <- components/AgentStreamingConsole.tsx"
echo "POST /api/jobs                 <- components/AgentStreamingConsole.tsx"
echo "GET  /api/jobs/:id             <- components/AgentStreamingConsole.tsx"
echo "POST /api/stripe/checkout      <- app/marketplace/page.tsx"

echo
echo "== Backend routes live check =="

check_route() {
  local name="$1"
  local method="$2"
  local path="$3"
  local body="${4:-}"

  local out status
  local auth_header=()
  if [[ -n "$AUTH_TOKEN" ]]; then
    auth_header=(-H "Authorization: Bearer $AUTH_TOKEN")
  fi

  if [[ "$method" == "GET" ]]; then
    out=$(curl -sS -o /tmp/connectivity_body.txt -w "%{http_code}" "${auth_header[@]}" "$BASE_URL$path")
  else
    out=$(curl -sS -o /tmp/connectivity_body.txt -w "%{http_code}" -X "$method" "${auth_header[@]}" -H "Content-Type: application/json" -d "$body" "$BASE_URL$path")
  fi
  status="$out"
  local preview
  preview=$(tr -d '\n' < /tmp/connectivity_body.txt | head -c 180)
  echo "$method $path | status=$status | $name"
  echo "  body: $preview"
}

if [[ -z "$AUTH_TOKEN" ]]; then
  echo "Mode: no AUTH_TOKEN (expect protected routes -> 401)"
else
  echo "Mode: AUTH_TOKEN provided (expect protected routes -> non-401)"
fi

check_route "frontend call" "POST" "/api/orchestrator/stream" '{"industry":"SaaS","product":"Demo","audience":"marketer"}'
check_route "frontend call" "POST" "/api/jobs" '{"prompt":"demo"}'
check_route "frontend call (needs real id)" "GET" "/api/jobs/test-id"
check_route "frontend call" "POST" "/api/stripe/checkout" '{"name":"Pack A","slug":"pack-a","price":199000}'

echo
echo "== Additional backend routes =="
check_route "backend only" "POST" "/api/image/generate" '{"prompt":"banner ad for skincare"}'
check_route "backend only / env dependent" "GET" "/api/tiktok/oauth-url"
check_route "backend only" "POST" "/api/tiktok/direct-post" '{"videoUrl":"https://example.com/video.mp4","caption":"demo"}'
check_route "backend only" "POST" "/api/tiktok/campaign" '{"name":"Demo","objectiveType":"CONVERSIONS","budget":500000}'
