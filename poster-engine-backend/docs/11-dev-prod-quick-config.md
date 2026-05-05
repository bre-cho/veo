# 11 - DEV/PROD Quick Config

Muc tieu tai lieu nay:
- Co bo cau hinh nhanh de chay local (DEV) va production-like (PROD).
- Co mau env day du cho auth, provider adapters, storage va billing.
- Co cach thu endpoint token noi bo cho moi truong dev.

## 1) DEV quick start

```bash
cp .env.example .env
docker compose up --build
```

Che do de dev nhanh:
- `ADOBE_MODE=mock`
- `CANVA_MODE=mock`
- `STORAGE_PROVIDER=local`
- `APP_ENV=local`

## 2) PROD-like quick start

Neu muon test production adapters/storage tren staging:
- `APP_ENV=staging`
- `ADOBE_MODE=production`
- `CANVA_MODE=production`
- `STORAGE_PROVIDER=s3`

Luu y:
- Endpoint `/internal/dev/token` se bi khoa khi `APP_ENV=production`.
- Khong commit secret that.

## 3) Env example day du

```bash
APP_ENV=local
DATABASE_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/poster_engine
REDIS_URL=redis://redis:6379/0
STORAGE_DIR=/data/storage

# Adobe
ADOBE_MODE=mock
ADOBE_API_KEY=
ADOBE_CLIENT_ID=
ADOBE_API_BASE_URL=https://firefly-api.adobe.io
ADOBE_POLL_INTERVAL_SECONDS=1.0
ADOBE_POLL_MAX_ATTEMPTS=20

# Canva
CANVA_MODE=mock
CANVA_CLIENT_ID=
CANVA_CLIENT_SECRET=
CANVA_ACCESS_TOKEN=
CANVA_API_BASE_URL=https://api.canva.com

# API/Auth
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
AUTH_JWT_SECRET=change-me
AUTH_JWT_ALGORITHM=HS256
DEV_INTERNAL_TOKEN_SECRET=dev-internal-secret

# Runtime
API_BUDGET_PER_PROJECT=100
IDEMPOTENCY_TTL_SECONDS=3600
REQUEST_LOG_LEVEL=INFO

# Storage (S3/MinIO)
STORAGE_PROVIDER=local
STORAGE_BUCKET=poster-engine
STORAGE_REGION=us-east-1
STORAGE_ENDPOINT_URL=
STORAGE_ACCESS_KEY_ID=
STORAGE_SECRET_ACCESS_KEY=
STORAGE_SIGNED_URL_EXPIRY_SECONDS=86400

# Billing
BILLING_DEFAULT_QUOTA_PER_MONTH=1000
```

MinIO mau:
```bash
STORAGE_PROVIDER=s3
STORAGE_ENDPOINT_URL=http://minio:9000
STORAGE_ACCESS_KEY_ID=minioadmin
STORAGE_SECRET_ACCESS_KEY=minioadmin
STORAGE_BUCKET=poster-engine
```

## 4) Thu endpoint dev token noi bo

Yeu cau:
- `APP_ENV` khong phai `production`
- Header `x-dev-internal-secret` khop `DEV_INTERNAL_TOKEN_SECRET`

Tao token:

```bash
curl -sS -X POST "http://localhost:8000/internal/dev/token" \
  -H "Content-Type: application/json" \
  -H "x-dev-internal-secret: dev-internal-secret" \
  -d '{
    "user_id":"dev-user-1",
    "email":"dev@example.com",
    "workspace_id":"ws-dev",
    "expires_in_seconds":3600
  }'
```

Dung token goi API:

```bash
TOKEN=$(curl -sS -X POST "http://localhost:8000/internal/dev/token" \
  -H "Content-Type: application/json" \
  -H "x-dev-internal-secret: dev-internal-secret" \
  -d '{"user_id":"dev-user-1"}' | python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

curl -sS "http://localhost:8000/api/v1/billing/summary" \
  -H "Authorization: Bearer $TOKEN"
```

## 5) Provider endpoint mapping dang dung

Adobe production adapter:
- Submit: `POST /v3/images/generate-async`
- Poll: `GET /v3/images/operations/{operation_id}`

Canva production adapter:
- Submit: `POST /rest/v1/autofills`
- Poll: `GET /rest/v1/autofills/{job_id}`

Neu tai khoan cua ban co endpoint path/version khac, cap nhat `ADOBE_API_BASE_URL` va `CANVA_API_BASE_URL`, dong thoi map lai payload/headers trong adapters.
