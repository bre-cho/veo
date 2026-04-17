#!/usr/bin/env bash
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 PRODUCTION READINESS TEST"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

PASSED=0
FAILED=0
WARNINGS=0

is_service_up() {
    local service="$1"
    docker compose ps --status running "$service" 2>/dev/null | grep -q "$service"
}

test_step() {
    local name="$1"
    local command="$2"

    echo "Testing: $name..."
    if eval "$command" > /tmp/test_output.txt 2>&1; then
        echo "✅ PASS: $name"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo "❌ FAIL: $name"
        cat /tmp/test_output.txt
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# 1. Services
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 SERVICES CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker compose ps
echo ""

test_step "API Container Running" "docker compose ps api | grep -q 'Up'" || true
test_step "PostgreSQL Container Running" "docker compose ps postgres | grep -q 'Up'" || true
test_step "Redis Container Running" "docker compose ps redis | grep -q 'Up'" || true
echo ""

# 2. API Health
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏥 API HEALTH"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if is_service_up "api"; then
    test_step "API Health Endpoint" "curl -sf http://localhost:8000/healthz | jq -e '.ok == true'" || true
    test_step "API Health - PostgreSQL" "curl -sf http://localhost:8000/healthz | jq -e '(.postgres == \"ok\") or any(.checks[]?; .service == \"postgres\" and .ok == true)'" || true
    test_step "API Health - Redis" "curl -sf http://localhost:8000/healthz | jq -e '(.redis == \"ok\") or any(.checks[]?; .service == \"redis\" and .ok == true)'" || true
    test_step "API Health - Object Storage" "curl -sf http://localhost:8000/healthz | jq -e '(.object_storage == \"ok\") or any(.checks[]?; .service == \"object_storage\" and .ok == true)'" || true
    test_step "API Health - Workers" "curl -sf http://localhost:8000/healthz | jq -e '(.workers == \"ok\") or any(.checks[]?; .service == \"workers\" and .ok == true)'" || true
else
    echo "⚠️  Skipping API health checks: api service is not running"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# 3. Database
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🗄️  DATABASE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_step "Database Connection (SQLAlchemy 2.x)" "
docker compose exec -T api python << 'PYEOF'
from sqlalchemy import create_engine, text
import os
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1')).scalar()
    assert result == 1
PYEOF
" || true
echo ""

# 4. Redis
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📮 REDIS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_step "Redis Connection" "docker compose exec -T redis redis-cli PING | grep -q PONG" || true
echo ""

# 5. API Endpoints
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 API ENDPOINTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if is_service_up "api"; then
    test_step "API Docs Accessible" "curl -sf http://localhost:8000/docs > /dev/null" || true
    test_step "OpenAPI Schema" "curl -sf http://localhost:8000/openapi.json | jq . > /dev/null" || true
else
    echo "⚠️  Skipping API endpoint checks: api service is not running"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# 6. Warnings Check
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  WARNINGS CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! grep -q "ARTIFACT_SHARD" .env 2>/dev/null; then
    echo "⚠️  ARTIFACT_SHARD not set in .env (non-critical)"
    WARNINGS=$((WARNINGS + 1))
fi

if grep -q "^version:" docker-compose.yml 2>/dev/null; then
    echo "⚠️  docker-compose.yml has obsolete 'version' field (cosmetic)"
    WARNINGS=$((WARNINGS + 1))
fi

if [ $WARNINGS -eq 0 ]; then
    echo "✅ No warnings"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 TEST SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"
echo "⚠️  Warnings: $WARNINGS"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED - PRODUCTION READY!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
else
    echo "❌ SOME TESTS FAILED - REVIEW REQUIRED"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
fi