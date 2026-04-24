
# Final Merge Checklist

## 1) Package + imports
- [ ] Copy `backend/app/drama` into target monorepo without deleting existing render modules.
- [ ] Normalize `app.api.deps`, `app.db.base_class`, `app.db.session` imports.
- [ ] Ensure `backend/app/drama/api/__init__.py` is imported by your main API registration layer.
- [ ] Confirm all `__init__.py` files are present and package discovery works.

## 2) Database layer
- [ ] Add drama models to the SQLAlchemy model registry if your repo requires explicit imports.
- [ ] Create Alembic migrations for:
  - `drama_character_profiles`
  - `drama_character_states`
  - `drama_relationship_edges`
  - `drama_scene_states`
  - `drama_memory_traces`
  - `drama_arc_progress`
- [ ] Validate UUID strategy against your existing DB conventions.

## 3) API layer
- [ ] Register all drama routers.
- [ ] Verify prefixes do not collide with existing `/api/v1/*` namespaces.
- [ ] Protect admin endpoints with your auth/admin dependency if needed.

## 4) Worker layer
- [ ] Adapt `@shared_task` / worker decorators to your queue stack.
- [ ] Bind `drama_scene_worker` and `continuity_rebuild_worker` to actual queue names.
- [ ] Wire retry policy from `backend/app/drama/ops/worker_retry_policy.py`.
- [ ] Implement dead-letter handling from `docs/dead_letter_policy.md`.

## 5) Integration discipline
- [ ] Keep drama compile output as source-of-truth for render prompt generation.
- [ ] Do not let render layer override power hierarchy, exposure state, or blocking notes.
- [ ] Keep this patch additive; do not rewrite provider adapters or render core in the same PR.

## 6) Recommended merge sequence
1. models + schemas + rules
2. services + engines
3. API routers
4. workers + ops
5. app registration + migrations + smoke tests
