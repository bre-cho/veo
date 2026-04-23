# merge_order.md

## Objective
Add avatar tournament + governance with the least-risk merge path:
- additive DB/models first
- isolated services second
- feedback wiring third
- decision/render wiring fourth
- ops/debug endpoints last

---

## Merge 7 — Schema + model foundation
Add only new tables/models/schemas first. No behavior changes yet.

### Add
- `backend/app/models/avatar_tournament_run.py`
- `backend/app/models/avatar_match_result.py`
- `backend/app/models/avatar_policy_state.py`
- `backend/app/models/avatar_promotion_event.py`
- `backend/app/models/avatar_guardrail_event.py`
- `backend/app/schemas/avatar_tournament.py`
- `backend/app/schemas/avatar_governance.py`
- `backend/app/schemas/avatar_selection_debug.py`

### Also
- Add migration from `schema.sql`
- Ensure imports do not create circular dependency

### Verify
- app boots
- ORM models import cleanly
- migration up/down works
- no route/service behavior changed yet

---

## Merge 8 — Isolated engines
Add independent services that can be tested in isolation before they influence production flow.

### Add
- `backend/app/services/avatar/avatar_tournament_engine.py`
- `backend/app/services/avatar/avatar_governance_engine.py`
- `backend/app/services/avatar/avatar_policy_engine.py`
- `backend/app/services/avatar/avatar_weight_engine.py`
- `backend/app/services/avatar/avatar_pair_learning_engine.py`
- `backend/app/services/avatar/avatar_rollback_service.py`
- `backend/app/services/avatar/avatar_selection_explainer.py`

### Verify
- service unit tests pass
- tournament engine ranks candidates with dummy data
- governance engine computes state transitions without touching publish/render paths
- fallback path exists when historical data is empty

---

## Merge 9 — Feedback learning path
Wire actual outcomes into tournament/governance tables before using tournament to make live decisions.

### Modify
- `backend/app/services/avatar/avatar_scorecard.py`
- `backend/app/services/avatar/avatar_pair_optimizer.py`
- `backend/app/services/brain/brain_feedback_service.py`

### Goal
- save predicted metrics into tournament result rows
- save actual metrics after publish
- compute fitness and state transitions offline/softly

### Verify
- after publish metrics arrive, `avatar_match_results` gets actual values
- `avatar_policy_states` is created/updated
- promotion/guardrail events are written
- no effect on avatar selection yet

---

## Merge 10 — Decision path injection
Now let the brain use tournament ranking in a soft-fail way.

### Modify
- `backend/app/services/brain/brain_decision_engine.py`
- `backend/app/services/publish/publish_scheduler.py`

### Goal
- select avatar through tournament when available
- keep stable fallback if tournament layer degrades
- preserve exploration ratio
- respect cooldown/blocked states

### Verify
- decision payload contains selected avatar
- scheduler skips cooldown avatars
- stable fallback still works if tournament engine errors
- no hard regression in preview/project flow

---

## Merge 11 — Render bridge injection
Attach selection/debug/policy data to execution metadata without changing core provider behavior.

### Modify
- `backend/app/services/render/execution_bridge_service.py`
- `backend/app/services/render/render_execution.py`

### Goal
- trace exactly why one avatar was chosen
- persist tournament and policy metadata with the execution

### Verify
- render manifest includes `avatar_id`
- render manifest includes `avatar_tournament_run_id`
- render manifest includes selection mode/reason
- provider adapters still receive valid payloads

---

## Merge 12 — Debug + ops routes
Expose read/ops endpoints after core wiring is stable.

### Add
- `backend/app/api/avatar_tournament.py`
- `backend/app/api/avatar_governance.py`

### Verify
- `POST /api/v1/avatar/tournament/run` works
- `GET /api/v1/avatar/tournament/{run_id}` works
- `GET /api/v1/avatar/governance/state/{avatar_id}` works
- rollback/cooldown endpoint updates policy state as expected

---

## Recommended rollback strategy by merge
If anything breaks:

### Rollback from Merge 12
- disable new API routers only

### Rollback from Merge 11
- remove render metadata injection
- keep tournament/governance persistence intact

### Rollback from Merge 10
- switch brain decision back to current stable avatar selection path
- keep offline feedback collection intact

### Rollback from Merge 9
- stop writing governance actions, keep tables/migrations

### Rollback from Merge 8
- keep DB foundation, disable service imports

### Rollback from Merge 7
- only if migration itself is invalid

---

## Smoke checklist after full pack
1. Migrate DB
2. Boot API
3. Boot worker
4. Create or load 2–3 avatars
5. Run manual tournament
6. Confirm one avatar selected
7. Start one render
8. Confirm render metadata has avatar context
9. Feed mock publish metrics
10. Confirm policy state changes
11. Trigger poor retention
12. Confirm cooldown or rollback
13. Run next tournament
14. Confirm ranking/selection changed accordingly

---

## Production hard rules
- tournament/governance must soft-fail, never hard-block render by default
- blocked/retired avatars never auto-schedule
- cooldown avatars require manual override or cooldown expiry
- priority avatars cannot consume 100% traffic; exploration must remain alive
- pair winners matter more than raw avatar winners

---

## Fastest safe implementation order
If you want the shortest path to visible value:

1. Merge 7
2. Merge 8
3. Merge 9
4. Run offline data collection for a few cycles
5. Merge 10 with fallback
6. Merge 11
7. Merge 12
