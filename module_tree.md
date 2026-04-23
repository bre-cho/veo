# MULTI_CHARACTER_DRAMA_ENGINE — module_tree.md

## Goal
Add a repo-ready **multi-character drama layer** to the existing avatar/video monorepo without rewriting render core.  
This patch introduces:

- character psychology state
- directional relationship graph
- scene tension / subtext / power-shift engines
- continuity memory across scenes / episodes
- drama-aware blocking + camera planning
- adapters that feed existing acting/render pipelines

This patch is designed to wrap existing systems rather than replace them.

---

## Monorepo tree to add

```text
backend/
  app/
    drama/
      __init__.py

      api/
        __init__.py
        drama_characters.py
        drama_relationships.py
        drama_scenes.py
        drama_arcs.py
        drama_compile.py

      models/
        __init__.py
        drama_character_profile.py
        drama_character_state.py
        drama_relationship_edge.py
        drama_scene_state.py
        drama_dialogue_subtext.py
        drama_power_shift.py
        drama_memory_trace.py
        drama_arc_progress.py
        drama_blocking_plan.py
        drama_camera_plan.py

      schemas/
        __init__.py
        character.py
        relationship.py
        scene_drama.py
        dialogue_subtext.py
        power_shift.py
        memory_trace.py
        arc_progress.py
        blocking.py
        camera_plan.py
        compile.py

      services/
        __init__.py
        cast_service.py
        relationship_service.py
        scene_drama_service.py
        dialogue_drama_service.py
        continuity_service.py
        arc_service.py
        drama_compile_service.py
        prompt_bridge_service.py

      engines/
        __init__.py
        character_intent_engine.py
        relationship_engine.py
        tension_engine.py
        subtext_engine.py
        power_shift_engine.py
        emotional_update_engine.py
        betrayal_alliance_engine.py
        chemistry_engine.py
        blocking_engine.py
        camera_drama_engine.py
        arc_engine.py
        continuity_engine.py

      rules/
        archetype_presets.yaml
        pressure_responses.yaml
        relation_shift_rules.yaml
        drama_event_rules.yaml
        camera_psychology_rules.yaml

      prompts/
        scene_tension_prompt.md
        dialogue_subtext_prompt.md
        power_shift_prompt.md
        blocking_prompt.md
        arc_update_prompt.md

      workers/
        drama_scene_worker.py
        drama_arc_worker.py
        continuity_rebuild_worker.py

      integrations/
        acting_adapter.py
        storyboard_adapter.py
        render_prompt_adapter.py
        project_workspace_adapter.py

backend/
  alembic/
    versions/
      20260423_0001_create_drama_core_tables.py
      20260423_0002_create_drama_output_tables.py
      20260423_0003_add_drama_indexes_and_constraints.py

frontend/
  app/
    drama/
      page.tsx
      characters/
        page.tsx
        [id]/
          page.tsx
      relationships/
        page.tsx
      scenes/
        [sceneId]/
          page.tsx
      arcs/
        [characterId]/
          page.tsx

frontend/
  components/
    drama/
      CharacterCard.tsx
      RelationshipGraph.tsx
      SceneTensionPanel.tsx
      PowerShiftTimeline.tsx
      BlockingPreview.tsx
      CameraPlanPanel.tsx
      ArcProgressPanel.tsx

frontend/
  lib/
    drama-api.ts
    drama-types.ts
```

---

## Responsibilities by layer

### `models/`
Persistent source of truth for drama state.

### `schemas/`
Pydantic I/O contracts for API + worker payloads.

### `engines/`
Pure business logic / scoring / derivation.

### `services/`
Use-case orchestration and DB transaction boundaries.

### `workers/`
Async recompute for scene chains and continuity rebuild.

### `integrations/`
Safe bridge into current acting / storyboard / prompt / render stack.

---

## Engine contracts

### `character_intent_engine.py`
Inputs:
- profile
- current state
- scene beat
- relation graph

Outputs:
- visible objective
- hidden objective
- fear trigger
- likely defense
- likely subtext

### `relationship_engine.py`
Inputs:
- prior directional edge A->B
- prior directional edge B->A
- scene outcome
- interaction tags

Outputs:
- updated trust / resentment / dependence / attraction / fear / dominance deltas

### `tension_engine.py`
Computes:
- scene tension score
- visible conflict
- hidden conflict
- exposure risk
- time pressure
- social consequence
- flat-scene flag

### `subtext_engine.py`
Maps each line / beat to:
- literal intent
- hidden intent
- psychological action
- honesty level
- mask level
- target reaction pressure

### `power_shift_engine.py`
Tracks:
- social power
- emotional power
- informational power
- moral power
- spatial power
- narrative control

### `emotional_update_engine.py`
Mandatory pipeline:
`scene_outcome -> emotional_state_shift -> relationship_shift -> memory_trace_update -> arc_stage_update`

### `blocking_engine.py`
Outputs:
- distance strategy
- entry/exit ownership
- center-frame ownership
- eye-line pattern
- body orientation
- pressure movement

### `camera_drama_engine.py`
Outputs drama-aware camera plan using:
- power state
- exposure risk
- scene temperature
- blocking plan
- continuity notes

Camera rules are aligned with the uploaded camera guides, including static/pan/tilt/push-in/dolly/arc/overhead/low-angle/high-angle/dutch/OTS/tracking/whip-pan/slow-mo and timing usage guidance. fileciteturn0file0L1-L33 fileciteturn0file1L25-L100

### `arc_engine.py`
Tracks per character:
- false belief
- pressure
- mask break
- truth acceptance
- collapse risk
- transformation progress

### `continuity_engine.py`
Rebuilds downstream scene state when upstream scene changes.

---

## Safe integration points into existing repo

Do **not** replace these core modules in the first merge:
- render execution core
- provider adapters
- template runtime
- project workspace
- existing avatar acting modules

Instead add wrappers:

```text
existing script/scene data
  -> drama compile
  -> acting adapter enrichment
  -> storyboard adapter enrichment
  -> render prompt adapter enrichment
  -> existing render pipeline
```

---

## Output objects for render bridge

### Acting enrichment
- tempo override
- gaze pattern
- movement density
- pause pattern
- mask/openness blend
- pressure behavior

### Storyboard enrichment
- who owns frame
- blocking power map
- reveal timing
- lens psychology suggestion
- shot duration hint

### Prompt enrichment
- camera move
- framing psychology
- emotional lighting
- continuity carry-over
- scene transition note

These mappings explicitly leverage the user’s uploaded Hollywood-style camera movement taxonomy and angle semantics so camera is not decorative but psychology-driven. fileciteturn0file0L1-L49 fileciteturn0file1L1-L74

---

## Rules files

### `archetype_presets.yaml`
Seed acting profiles from:
- Mentor
- Manipulator
- Rebel
- WoundedObserver
- Authority

### `pressure_responses.yaml`
Maps pressure trigger -> behavioral defense by archetype.

### `relation_shift_rules.yaml`
Rules for betrayal, reassurance, exposure, victory, humiliation, confession.

### `drama_event_rules.yaml`
Scene outcome taxonomy:
- betrayal
- public defeat
- private confession
- false accusation
- rescue
- abandonment
- frame control flip
- loyalty test
- secret reveal

### `camera_psychology_rules.yaml`
Maps drama state to camera language, including:
- low angle -> authority / pressure
- high angle -> weakness / exposure
- overhead -> isolation / system view
- OTS -> controlled confrontation
- dutch -> psychological instability
- push-in -> realization / emotional compression
- arc -> relation complexity / unstable alignment
- handheld -> raw instability
- slow motion -> emotional emphasis
- whip / speed-ramp -> transition shock or urgency fileciteturn0file0L15-L49 fileciteturn0file1L75-L123

---

## Minimal router registration

Add to main API router:
- `/api/v1/drama/characters`
- `/api/v1/drama/relationships`
- `/api/v1/drama/scenes`
- `/api/v1/drama/arcs`
- `/api/v1/drama/compile`

---

## Frontend views

### `/drama`
System dashboard:
- active projects
- latest recomputes
- continuity warnings
- unresolved tension scenes

### `/drama/characters/[id]`
- profile
- current emotional state
- arc state
- memory traces

### `/drama/relationships`
- graph view
- edge details
- change history

### `/drama/scenes/[sceneId]`
- tension score
- hidden conflict
- power shifts
- blocking plan
- camera plan
- continuity deltas

### `/drama/arcs/[characterId]`
- arc stage timeline
- belief shifts
- mask break progression

---

## Environment additions

```text
DRAMA_ENGINE_ENABLED=true
DRAMA_CONTINUITY_ASYNC=true
DRAMA_PROMPT_BRIDGE_ENABLED=true
DRAMA_CAMERA_RULESET=hollywood_psychology_v1
DRAMA_MAX_SCENE_REBUILD_DEPTH=24
```

---

## Testing targets

Add tests:
```text
backend/tests/drama/test_character_intent_engine.py
backend/tests/drama/test_relationship_engine.py
backend/tests/drama/test_tension_engine.py
backend/tests/drama/test_power_shift_engine.py
backend/tests/drama/test_continuity_engine.py
backend/tests/api/test_drama_routes.py
```

---

## Non-goals for first merge
Not in phase 1:
- autonomous script writing
- full LLM-only improvisation
- full crowd-simulation
- voice synthesis replacement
- render-core rewrite
