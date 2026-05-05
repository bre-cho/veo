# 03 — Database

The current MVP creates tables from SQLAlchemy models at app startup for speed.

## Production Patch

Replace startup table creation with Alembic migrations.

Recommended command:

```bash
alembic init migrations
alembic revision --autogenerate -m "init poster engine schema"
alembic upgrade head
```

## Core Tables

- `brands`
- `projects`
- `assets`
- `poster_variants`
- `jobs`

## Required Migration Hardening

- Enforce foreign keys.
- Add indexes on `project_id`, `brand_id`, `created_at`.
- Add enum migrations for project/job statuses.
- Add checksum uniqueness if using artifact deduplication.
