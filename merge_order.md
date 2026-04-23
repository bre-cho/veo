# MULTI_CHARACTER_DRAMA_ENGINE — merge_order.md

## Merge goal
Introduce the drama engine in **safe additive phases** so the current avatar/video system keeps running while drama intelligence grows around it.

Do **not** start by touching render core.

---

## PHASE 1 — Foundation tables + models + schemas
**Risk:** Low  
**Why first:** Creates stable persistence contract without touching execution flow.

### Add
- `schema.sql` equivalent via Alembic
- all `models/`
- all `schemas/`
- `rules/archetype_presets.yaml`
- `rules/camera_psychology_rules.yaml`
- minimal CRUD APIs:
  - characters
  - relationships
  - arcs read
- frontend stubs optional

### Verify
- migration up succeeds
- create character works
- create relationship works
- list graph works
- no existing route regression

### Stop criteria
Only proceed when DB + CRUD are stable.

---

## PHASE 2 — Scene analysis core
**Risk:** Medium-low  
**Why second:** Scene intelligence can run in isolation and return JSON before touching render.

### Add
- `character_intent_engine.py`
- `relationship_engine.py`
- `tension_engine.py`
- `subtext_engine.py`
- `power_shift_engine.py`
- `scene_drama_service.py`
- `drama_scenes.py` analyze + compile routes

### Behavior
- accept scene text / beat payload
- return:
  - scene tension
  - conflict
  - subtext items
  - power shifts

### Verify
- analyze scene returns stable payload
- flat scene flag triggers correctly
- power shift rows persist
- repeated compile is idempotent

---

## PHASE 3 — Blocking + camera psychology
**Risk:** Medium  
**Why here:** Now that scene tension exists, camera/blocking can become consequence of psychology instead of decoration.

### Add
- `blocking_engine.py`
- `camera_drama_engine.py`
- `drama_blocking_plans` + `drama_camera_plans` usage
- scene endpoints:
  - `/blocking`
  - `/camera-plan`

### Critical rule
Camera mapping must use the uploaded Hollywood camera language:
- low/high/overhead/dutch/OTS
- static/pan/tilt/dolly/tracking/arc
- whip/speed-ramp/focus-pull/slow-mo
- timing hints per shot type fileciteturn0file0L1-L49 fileciteturn0file1L1-L123

### Verify
- confrontation scenes choose meaningful OTS / push-in / low/high angle patterns
- exposure scenes can trigger high-angle or overhead where appropriate
- power-holding scenes can trigger stable / minimal-move / low-angle plans
- camera plan stored and readable

---

## PHASE 4 — Outcome + continuity
**Risk:** Medium-high  
**Why here:** This is where state starts changing across scenes.

### Add
- `emotional_update_engine.py`
- `continuity_engine.py`
- `arc_engine.py`
- `continuity_service.py`
- `drama_arc_worker.py`
- `continuity_rebuild_worker.py`
- route:
  - `/apply-outcome`
  - `/arcs/{character_id}/advance`
  - `/arcs/recompute`

### Mandatory law
`scene outcome -> emotional shift -> relationship shift -> memory trace -> arc update`

### Verify
- betrayal lowers trust and raises resentment
- confession reduces mask_strength and can raise openness
- updating scene N rebuilds state for N+1 onward
- continuity warnings appear on contradictions

---

## PHASE 5 — Render bridge
**Risk:** Medium-high  
**Why now:** Only bridge once drama outputs are already stable.

### Add
- `acting_adapter.py`
- `storyboard_adapter.py`
- `render_prompt_adapter.py`
- `prompt_bridge_service.py`

### Integration rule
Do not rewrite render core.  
Only enrich existing payloads with:
- acting hints
- blocking notes
- camera notes
- continuity notes
- lighting psychology

### Verify
- existing render still works with bridge disabled
- existing render works with bridge enabled
- prompt payload now contains drama-aware camera language
- acting payload reflects archetype + live pressure state

---

## PHASE 6 — Episode/project compile + UI
**Risk:** Medium  
**Why after backend stabilization:** mostly orchestration and visibility.

### Add
- `drama_compile_service.py`
- `/compile/episode`
- `/compile/project`
- frontend panels:
  - relationship graph
  - scene tension panel
  - blocking preview
  - camera plan
  - arc progress

### Verify
- episode compile surfaces continuity warnings
- graph UI reflects directional edges
- scene detail page shows subtext + power shifts + camera plan

---

## PHASE 7 — Advanced optional upgrades
**Risk:** Higher  
**Defer until core stable**

### Add later
- chemistry engine
- betrayal prediction model
- scene tournament
- best-scene variant ranking
- winner DNA memory for relationship archetypes
- multi-episode drama optimization

---

## File-by-file recommended order

### 1. Database first
1. alembic migration 0001 core tables
2. alembic migration 0002 output tables
3. alembic migration 0003 indexes and constraints

### 2. Core contracts
4. models/*
5. schemas/*

### 3. Low-risk APIs
6. api/drama_characters.py
7. api/drama_relationships.py

### 4. Core engines
8. engines/character_intent_engine.py
9. engines/relationship_engine.py
10. engines/tension_engine.py
11. engines/subtext_engine.py
12. engines/power_shift_engine.py

### 5. Scene service + routes
13. services/scene_drama_service.py
14. api/drama_scenes.py

### 6. Spatial/camera layer
15. engines/blocking_engine.py
16. engines/camera_drama_engine.py

### 7. Continuity layer
17. engines/emotional_update_engine.py
18. engines/continuity_engine.py
19. engines/arc_engine.py
20. services/continuity_service.py
21. services/arc_service.py
22. api/drama_arcs.py

### 8. Bridge layer
23. integrations/acting_adapter.py
24. integrations/storyboard_adapter.py
25. integrations/render_prompt_adapter.py
26. services/prompt_bridge_service.py

### 9. Compile layer
27. services/drama_compile_service.py
28. api/drama_compile.py

### 10. Async + UI
29. workers/*
30. frontend/drama/*
31. components/drama/*

---

## Rollback strategy

If any issue appears:
1. set `DRAMA_ENGINE_ENABLED=false`
2. keep tables, but skip enrichment
3. leave render core untouched
4. disable workers:
   - drama_scene_worker
   - drama_arc_worker
   - continuity_rebuild_worker

Because the patch is additive, rollback should be runtime-flag first, not schema delete.

---

## Minimal smoke test plan

### After phase 1
- create 2 characters
- create 2 directional edges
- read graph

### After phase 2
- compile one confrontation scene
- confirm tension score + subtext + power shifts exist

### After phase 3
- confirm camera plan includes psychologically valid move
- confirm blocking plan includes center-frame ownership or eye-line strategy

### After phase 4
- apply betrayal outcome
- confirm trust down / resentment up / memory trace created / arc updated

### After phase 5
- render one scene with drama bridge enabled
- compare prompt payload before vs after

### After phase 6
- compile full episode
- confirm continuity warnings present if contradictions exist
