# Render Factory Monorepo (merged)

This repository is a merged monorepo assembled from the user-provided render pipeline bundles and code snippets in the current conversation and file library.

## Scope included
- FastAPI backend API
- Frontend UI (Next.js)
- Celery workers
- Redis / Postgres
- Alembic migrations
- Provider abstraction
- Veo / Runway / Kling adapters
- Webhook callback ingestion
- Poll fallback
- Object storage / MinIO / signed URL
- Render job status API
- Healthcheck
- Docker compose
- `.env.example`
- `Makefile`
- basic tests / smoke checks
- local dev docs

## Provenance
Primary base: `render_factory_repo.zip`.
Supplemental merges:
- `template_engine_bundle(2).zip` for frontend scaffold and script upload patterns.
- `full_render_pipeline_and_bandit_bundle.zip` for realtime progress widget.
- snippets from uploaded text/library for the locked render execution chain and preview-first editing flow.

## Current state
This is the most complete merged repo I could assemble from the available sources.
Parts explicitly marked mock or TODO are integration points where the source material only contained scaffolding or intentionally mocked provider calls.

## Quick start
```bash
cp backend/.env.example backend/.env.dev
cp frontend/.env.local.example frontend/.env.local
docker compose up --build
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- Flower: http://localhost:5555
- MinIO console: http://localhost:9001

## Main pipeline
1. Upload `.txt` / `.docx` script
2. Build preview payload
3. Edit / validate preview
4. Create project from confirmed preview
5. Prepare provider-specific plan / payloads
6. Create render job
7. Dispatch scene tasks to provider adapters
8. Provider callback and/or polling updates scene state
9. Upload assets to object storage
10. Merge clips + burn subtitles
11. Expose final status and final video URL

## Avatar Tournament + Avatar Governance skeleton notes

This repository now also includes additive skeleton modules for avatar tournament/governance flow:

- SQLAlchemy models
- Pydantic schemas
- `services/avatar` tournament + governance engines
- FastAPI route skeletons

Integration notes:

- Replace `get_db()` stubs in new API files with your real DB session dependency.
- Register newly added models in metadata bootstrap and Alembic env.
- Include the new routers in the API app registry.
- Patch `brain_decision_engine`, `brain_feedback_service`, `publish_scheduler`, and `render_execution` service flows to call these modules.

Recommended next steps:

1. Add migrations for new tables.
2. Persist debug/explanation payloads with richer fields.
3. Implement DB-backed historical pair stats.
4. Replace placeholder scoring heuristics with production avatar engines.
