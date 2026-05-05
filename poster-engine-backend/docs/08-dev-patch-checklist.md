# 08 — Dev Patch Checklist

## Phase 1 — Stabilize MVP

- [x] Replace `Base.metadata.create_all` with Alembic migrations.
- [x] Add request IDs and structured logs.
- [x] Add error handler middleware.
- [x] Add pagination for variant list.
- [x] Add unit tests for prompt/scoring/provider contracts.

## Phase 2 — Provider Integration

- [ ] Implement real Adobe adapter.
- [ ] Implement real Canva adapter.
- [x] Add provider retries with backoff.
- [x] Add provider budget guard.
- [x] Store raw provider responses for audit.

## Phase 3 — Async Production

- [x] Move generation flow to Celery chain.
- [x] Add job events endpoint.
- [x] Add Redis progress updates.
- [x] Add idempotency keys.

## Phase 4 — Export + Storage

- [ ] Add S3/MinIO asset storage.
- [ ] Generate signed URLs.
- [ ] Add artifact contract: mime, size, checksum, source_job_id.
- [ ] Add replayability metadata.

## Phase 5 — Go Live

- [ ] Add auth.
- [ ] Add workspace/user ownership.
- [ ] Add billing/usage metering.
- [ ] Add Sentry and Prometheus.
- [ ] Add CI smoke tests.
