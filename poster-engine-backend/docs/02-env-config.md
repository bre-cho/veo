# 02 — Environment Config

Copy `.env.example` to `.env`.

## Required

```bash
DATABASE_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/poster_engine
REDIS_URL=redis://redis:6379/0
STORAGE_DIR=/data/storage
```

## Provider Mode

Use mock mode for local dev:

```bash
ADOBE_MODE=mock
CANVA_MODE=mock
```

Production mode should be enabled only after real adapters are implemented:

```bash
ADOBE_MODE=production
CANVA_MODE=production
```

Do not commit real API keys.
