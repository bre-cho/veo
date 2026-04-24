# Drama Workers — Phase 4 Persistence + Worker Loop

## Purpose
Phase 4 upgrades the drama engine from transient scene analysis to persistent operational state:
- scene analysis is stored
- memory traces survive across scenes and episodes
- arc state advances incrementally
- continuity can be rebuilt after manual scene edits

## Worker 1 — `drama_scene_worker.py`
### Responsibility
Process one scene end-to-end:
1. run scene analysis
2. build render bridge payload
3. persist `drama_scene_states`
4. generate `drama_memory_traces`
5. update `drama_arc_progress`

### Input contract
```json
{
  "scene_id": "uuid",
  "project_id": "uuid",
  "episode_id": "uuid",
  "scene_goal": "string",
  "characters": [
    {"character_id": "uuid", "role": "speaker|listener|observer"}
  ],
  "beats": [],
  "dialogue": []
}
```

### Output contract
```json
{
  "ok": true,
  "scene_id": "uuid",
  "analysis": {},
  "compile_payload": {},
  "memory_traces_created": 3
}
```

### Retry policy
Recommended:
- retry on transient DB errors
- retry on provider timeouts if analysis later uses external models
- do not auto-retry on schema validation bugs

## Worker 2 — `continuity_rebuild_worker.py`
### Responsibility
Recompute continuity reports across stored scene states after:
- mid-episode scene edits
- manual overrides
- arc repair passes
- migration backfills

### Output
Stores `continuity_payload` in each scene state row.

## Persistence tables touched
- `drama_scene_states`
- `drama_memory_traces`
- `drama_arc_progress`

## Operational recommendations
- run `process_scene` on scene create/update
- run `rebuild_continuity` on episode publish preview or after manual scene reorder
- add idempotency key if your queue system can dispatch duplicate jobs
- store job metrics: latency, scenes processed, continuity errors, arc updates, memory traces created

## Integration notes
Adapt these imports to the real monorepo:
- `app.db.session.SessionLocal`
- Celery task registration style
- logger / tracing / metrics adapters
- service DI container if used

## Suggested next patch
Phase 5 should add:
- `drama_memory` API router
- `drama_state` API router
- recall ranking service
- worker metrics and dead-letter handling
- downstream scene recompute fanout
