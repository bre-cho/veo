# Drama Engine Ops Runbook

## Scope
This runbook covers the phase-5 API and ops surface for drama memory, state queries, recompute flows, and worker reliability policy.

## Primary endpoints
- `GET /api/v1/drama/memory/characters/{character_id}`
- `GET /api/v1/drama/memory/characters/{character_id}/recall`
- `GET /api/v1/drama/state/scenes/{scene_id}`
- `GET /api/v1/drama/state/projects/{project_id}/dashboard`
- `POST /api/v1/drama/admin/episodes/{episode_id}/recompute`

## Standard operating checks
1. Confirm scene worker is writing `scene_drama_states`
2. Confirm memory traces are increasing after relationship-shift scenes
3. Confirm arc progression changes after major scene outcomes
4. Confirm dashboard endpoint reflects latest state counts
5. Confirm recompute endpoint returns drift report after edited scenes

## Incident classes
### A. Scene state missing
Symptoms:
- state endpoint returns 404
- compiler success exists but persistence record missing

Actions:
- inspect scene worker logs
- inspect DB write path for scene state insert/commit
- replay scene worker once
- if still failing, move job to dead letter and review payload

### B. Memory recall returns empty unexpectedly
Symptoms:
- memory list has rows but recall endpoint returns empty

Actions:
- verify `recall_trigger` and `meaning_label` are populated
- verify trigger string normalization
- inspect persistence/emotional weight defaults
- if data is valid, tune `MemoryRecallEngine` weights

### C. Continuity drift after mid-episode edit
Symptoms:
- continuity rebuild worker flags downstream breaks
- recompute endpoint returns non-zero `drift_count`

Actions:
- replay scene analysis from edited scene onward
- verify prior scene outcome types remain consistent
- if downstream state is contradictory, classify as `repair_then_rebuild`

## Metrics to watch
- `drama.scene_worker.success`
- `drama.scene_worker.failure`
- `drama.scene_worker.retry`
- `drama.continuity.break_count`
- `drama.memory.recall.hit`
- `drama.memory.recall.miss`
- `drama.recompute.drift_count`

## Escalation guidance
- Repeated 404 on latest scene state for a live project -> page backend owner
- Dead-letter growth > baseline for 3 consecutive cycles -> page pipeline owner
- Continuity drift on published episode candidate -> stop publish promotion and require manual review
