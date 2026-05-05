# Poster Engine Backend Production MVP

Backend production scaffold for Luxury Ads / Beauty Campaign poster generation.

Core flow:

```txt
Brand DNA → Project → Prompt Engine → Adobe Visual Adapter → Canva Layout Adapter → Scoring → Export Pack
```

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

API docs: http://localhost:8000/docs

## Main endpoints

- `POST /api/v1/brands`
- `POST /api/v1/projects`
- `POST /api/v1/projects/{project_id}/generate`
- `GET /api/v1/projects/{project_id}/variants`
- `POST /api/v1/variants/{variant_id}/score`
- `POST /api/v1/variants/{variant_id}/export`
- `GET /api/v1/jobs/{job_id}`

See `docs/` for dev patch instructions.

Quick config guide (DEV/PROD + internal dev token): `docs/11-dev-prod-quick-config.md`.
