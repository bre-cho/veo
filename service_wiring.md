# MULTI_CHARACTER_DRAMA_ENGINE — service_wiring.md

## Wiring goal
Attach drama intelligence to the current avatar/video stack without breaking:
- render execution
- provider adapters
- project workspace
- existing acting engine
- storyboard compiler

The drama layer should enrich scene context before rendering and persist continuity after outcomes.

---

## 1) Runtime wiring overview

```text
[project / episode / scene input]
        ->
[scene_drama_service.analyze_or_compile()]
        ->
[engines: intent + relation + tension + subtext + power + blocking + camera]
        ->
[prompt_bridge_service.build_render_bridge_payload()]
        ->
[existing acting/storyboard/render modules]
        ->
[render completed or scene outcome confirmed]
        ->
[continuity_service.apply_scene_outcome()]
        ->
[emotional update + relation update + memory traces + arc update]
```

---

## 2) Main service responsibilities

### `cast_service.py`
Purpose:
- CRUD character profiles
- apply archetype seed preset
- bootstrap initial state rows

Depends on:
- `drama_character_profile` model
- `drama_character_state` model
- `archetype_presets.yaml`

Notes:
- presets should seed acting defaults, not hard-lock final behavior
- safe place to map uploaded archetypes:
  - Mentor
  - Manipulator
  - Rebel
  - WoundedObserver
  - Authority

### `relationship_service.py`
Purpose:
- create/update directional edges
- rebuild graph cache
- expose relation summaries for UI and engines

Depends on:
- `relationship_engine.py`
- `drama_relationship_edge` model

### `scene_drama_service.py`
Purpose:
- entry point for scene analyze / compile
- load project characters + edges + prior scene state
- call all lower-level engines in correct order

Call order:
1. load participants
2. load directional edges
3. infer character intents
4. compute scene tension
5. compute dialogue subtext
6. compute power shifts
7. compute blocking plan
8. compute camera plan
9. persist scene outputs
10. optionally build render bridge payload

### `dialogue_drama_service.py`
Purpose:
- compile subtext rows from line-by-line scene content or beat list
- generate literal intent / hidden intent / psychological action
- tag lines for pressure or reveal

### `continuity_service.py`
Purpose:
- apply scene outcome
- update downstream emotional states
- update relationship edges
- write memory traces
- advance arc progress
- queue asynchronous downstream recompute

Mandatory update law:
`scene outcome -> emotional shift -> relationship shift -> memory trace -> arc stage`

### `arc_service.py`
Purpose:
- read/write arc progress
- recompute arc from episode or project
- detect mask-break and truth-acceptance jumps

### `drama_compile_service.py`
Purpose:
- compile entire episode or project drama package
- collect continuity warnings
- expose data to UI or export

### `prompt_bridge_service.py`
Purpose:
- convert drama outputs into payloads consumable by existing render stack
- should not render anything itself
- only enrich payloads

Bridge payload sections:
- acting_enrichment
- blocking_enrichment
- camera_enrichment
- continuity_notes
- lighting_psychology
- transition_hint

---

## 3) Engine wiring order

### analyze path
```text
scene_drama_service
  -> character_intent_engine
  -> tension_engine
  -> subtext_engine
  -> power_shift_engine
  -> blocking_engine
  -> camera_drama_engine
```

### apply outcome path
```text
continuity_service
  -> emotional_update_engine
  -> relationship_engine
  -> betrayal_alliance_engine
  -> chemistry_engine (optional recompute)
  -> continuity_engine
  -> arc_engine
```

---

## 4) Adapter wiring into current repo

## A. Acting adapter
File:
`backend/app/drama/integrations/acting_adapter.py`

Purpose:
Convert drama state into acting control hints.

Suggested output:
```json
{
  "character_id": "...",
  "tempo_override": "slow_tight",
  "gaze_pattern": "avoid_then_lock",
  "movement_density": "minimal_rigid",
  "pause_pattern": "long_loaded",
  "pressure_behavior": "deepen_calm",
  "mask_openness_blend": 0.42
}
```

Map archetype + live pressure to acting surface.

## B. Storyboard adapter
File:
`backend/app/drama/integrations/storyboard_adapter.py`

Purpose:
Inject:
- power holder
- emotional anchor
- blocking notes
- reveal timing
- shot duration hint

## C. Render prompt adapter
File:
`backend/app/drama/integrations/render_prompt_adapter.py`

Purpose:
Translate drama-aware camera and lighting plan into prompt fragments for existing provider adapters.

This adapter should use camera semantics grounded in the uploaded materials:
- static / pan / tilt / push-in / dolly / truck / arc
- overhead / low angle / high angle / OTS / tracking / dutch
- speed-ramp / slow motion / whip pan / focus pull
- timing guidance by phase (hook, demo, pressure, payoff) fileciteturn0file0L1-L49 fileciteturn0file1L75-L123

## D. Project workspace adapter
File:
`backend/app/drama/integrations/project_workspace_adapter.py`

Purpose:
Read scenes from current project workspace format and return normalized beat payloads for drama analysis.

---

## 5) FastAPI router wiring

In central router registration:

```python
from app.drama.api import (
    drama_characters,
    drama_relationships,
    drama_scenes,
    drama_arcs,
    drama_compile,
)

api_router.include_router(drama_characters.router, prefix="/drama/characters", tags=["drama-characters"])
api_router.include_router(drama_relationships.router, prefix="/drama/relationships", tags=["drama-relationships"])
api_router.include_router(drama_scenes.router, prefix="/drama/scenes", tags=["drama-scenes"])
api_router.include_router(drama_arcs.router, prefix="/drama/arcs", tags=["drama-arcs"])
api_router.include_router(drama_compile.router, prefix="/drama/compile", tags=["drama-compile"])
```

---

## 6) Celery / worker wiring

### `drama_scene_worker.py`
Trigger on:
- scene created
- scene edited
- user requests recompile
- episode compile

Tasks:
- analyze scene
- compile scene outputs
- persist plans
- emit telemetry event

### `continuity_rebuild_worker.py`
Trigger on:
- apply_scene_outcome with recompute_downstream=true
- upstream scene content changed

Tasks:
- walk following scenes in episode order
- rebuild emotional states
- rebuild relation shifts
- rebuild arc projections
- flag continuity breaks

### `drama_arc_worker.py`
Trigger on:
- episode compile
- explicit arc recompute
- major event types like betrayal / confession / collapse

Tasks:
- recalc arc scores
- update stage
- write warnings if arc jump is too large

---

## 7) Transaction boundaries

### Safe DB transaction pattern
Use one transaction for:
- scene state
- subtext items
- blocking plan
- camera plan
- power shifts

Use a separate transaction or async job for:
- downstream recompute
- long continuity rebuild
- project-level compile

Reason:
avoid tying user request latency to entire episode recompute.

---

## 8) Suggested dependency injection

### Scene path
```python
SceneDramaService(
    cast_service=CastService(...),
    relationship_service=RelationshipService(...),
    tension_engine=TensionEngine(...),
    subtext_engine=SubtextEngine(...),
    power_shift_engine=PowerShiftEngine(...),
    blocking_engine=BlockingEngine(...),
    camera_drama_engine=CameraDramaEngine(...),
    prompt_bridge_service=PromptBridgeService(...),
)
```

### Outcome path
```python
ContinuityService(
    emotional_update_engine=EmotionalUpdateEngine(...),
    relationship_engine=RelationshipEngine(...),
    betrayal_alliance_engine=BetrayalAllianceEngine(...),
    continuity_engine=ContinuityEngine(...),
    arc_engine=ArcEngine(...),
)
```

---

## 9) Camera + blocking mapping rules

Use uploaded camera files as deterministic rule input, not just inspiration.

### Scene camera mapping examples
- authority holds frame -> static / low-angle / controlled push-in
- weak exposure -> high-angle / longer hold / restricted movement
- system isolation -> overhead / top-down layout
- confrontation -> over-the-shoulder / tracking / push-in
- unstable psyche -> dutch / handheld / off-axis reveal
- emotional realization -> slow push-in / focus pull / pause hold
- relationship complexity -> arc move
- urgency / shock -> whip pan / speed ramp
- payoff -> crane or controlled pull-out depending emotional meaning fileciteturn0file0L15-L49 fileciteturn0file1L25-L123

### Shot duration hints
Use:
- 2–3s for establishing authority/emphasis angles
- 3–5s for tracking/dolly beats
- 4–6s for arc exploration
- 1–2s for dutch / whip / vertigo accents
These timing conventions are aligned with the uploaded guides. fileciteturn0file1L1-L24

---

## 10) Frontend data flow

### `/drama/scenes/[sceneId]`
API calls:
1. GET scene state
2. GET subtext
3. GET blocking plan
4. GET camera plan

### `/drama/relationships`
API calls:
1. GET graph
2. optional diff history endpoint later

### `/drama/arcs/[characterId]`
API calls:
1. GET arc timeline
2. optionally read latest memory traces

---

## 11) Telemetry wiring

Emit metrics on:
- tension_score
- flat_scene_flag
- power_shift_magnitude
- trust_shift_magnitude
- continuity_break_count
- arc_jump_warning_count
- render_bridge_applied

Suggested event names:
```text
drama.scene.compiled
drama.scene.flat_flagged
drama.scene.outcome.applied
drama.continuity.rebuild.completed
drama.arc.updated
drama.render_bridge.generated
```

---

## 12) Backward compatibility rules

1. If `DRAMA_ENGINE_ENABLED=false`, existing render flow must remain untouched.
2. If a scene has no drama state, render with current defaults.
3. `external_avatar_id` remains optional.
4. Do not require drama profiles for all projects in phase 1.
5. Missing camera plan should fall back to current storyboard camera defaults.

---

## 13) Verify checklist after merge

### API
- create character works
- apply preset works
- create directional relationship works
- analyze scene returns tension score
- compile scene persists subtext + blocking + camera
- apply outcome updates downstream state

### DB
- all drama tables migrate cleanly
- indexes created
- no conflicts with current tables

### Render bridge
- existing render route accepts drama enrichment without error
- scenes without drama still render normally

### Continuity
- editing scene N triggers downstream rebuild on scene N+1...N+k
