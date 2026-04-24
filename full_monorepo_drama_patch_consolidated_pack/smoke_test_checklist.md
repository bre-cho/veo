
# Smoke Test Checklist

Goal: verify the end-to-end drama path from CRUD -> analyze -> compile -> persist -> recall -> recompute.

## A. CRUD
- [ ] Create character A
- [ ] Create character B
- [ ] Read both characters
- [ ] Update one character preset / profile field
- [ ] Create directional relationship A -> B
- [ ] Create directional relationship B -> A
- [ ] Read relationship graph and confirm scores differ by direction

## B. Analyze
- [ ] POST `/api/v1/drama/scenes/analyze` with:
  - `project_id`
  - `scene_id`
  - `character_ids`
  - `scene_context`
- [ ] Verify response contains:
  - intents
  - tension
  - subtext_map
  - power_shift
  - dominant_character_id

## C. Compile
- [ ] POST `/api/v1/drama/compile/scene`
- [ ] Verify response contains:
  - blocking_plan
  - camera_plan
  - continuity_report
  - render_bridge_payload

## D. Persist
- [ ] Run `drama_scene_worker` for a scene
- [ ] Confirm DB persistence for:
  - scene state
  - memory traces
  - arc progress

## E. Recall
- [ ] GET drama memory endpoint for a character
- [ ] Confirm memory recall engine returns ranked traces or trigger matches
- [ ] Validate a betrayal/exposure event shows up in recall results

## F. Recompute
- [ ] Modify one early-scene input or stored scene state
- [ ] POST admin recompute endpoint for affected episode
- [ ] Confirm downstream scene states are recalculated
- [ ] Confirm continuity report changes where expected

## G. Operational checks
- [ ] Simulate one recoverable worker error and confirm retry policy path
- [ ] Simulate one non-recoverable worker error and confirm dead-letter path
- [ ] Confirm metrics facade emits at least scene analyze / compile / persist counters

## Minimum GO criteria
- [ ] No import errors on app start
- [ ] All routers registered
- [ ] Analyze + compile return 200
- [ ] Worker persists one full scene cycle
- [ ] Recall endpoint returns data
- [ ] Recompute endpoint completes successfully
