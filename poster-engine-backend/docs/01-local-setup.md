# 01 — Local Setup

## Requirements

- Docker Desktop
- Python 3.12 if running outside Docker

## Run

```bash
cp .env.example .env
docker compose up --build
```

Open:

```txt
http://localhost:8000/docs
```

## Smoke Test

In a separate terminal:

```bash
bash scripts/smoke_test.sh
```

Expected:

- Health returns OK.
- Brand is created.
- Project is created.
- 5 poster variants are generated.
