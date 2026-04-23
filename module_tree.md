# module_tree.md

```txt
backend/
└── app/
    ├── api/
    │   ├── avatar_governance.py
    │   └── avatar_tournament.py
    │
    ├── models/
    │   ├── avatar_guardrail_event.py
    │   ├── avatar_match_result.py
    │   ├── avatar_policy_state.py
    │   ├── avatar_promotion_event.py
    │   └── avatar_tournament_run.py
    │
    ├── schemas/
    │   ├── avatar_governance.py
    │   ├── avatar_selection_debug.py
    │   └── avatar_tournament.py
    │
    └── services/
        ├── avatar/
        │   ├── avatar_governance_engine.py
        │   ├── avatar_pair_learning_engine.py
        │   ├── avatar_policy_engine.py
        │   ├── avatar_rollback_service.py
        │   ├── avatar_selection_explainer.py
        │   ├── avatar_tournament_engine.py
        │   └── avatar_weight_engine.py
        │
        ├── brain/
        │   ├── brain_decision_engine.py          # modify
        │   └── brain_feedback_service.py         # modify
        │
        ├── publish/
        │   └── publish_scheduler.py              # modify
        │
        └── render/
            ├── execution_bridge_service.py       # modify
            └── render_execution.py               # modify
```

## Purpose by file

### API
- `api/avatar_tournament.py`
  - Manual tournament run endpoint
  - Tournament result detail endpoint
  - Candidate ranking + explanation output
- `api/avatar_governance.py`
  - Read avatar policy state
  - Recalculate avatar state
  - Force rollback / cooldown / reactivate for ops/debug

### Models
- `models/avatar_tournament_run.py`
  - Stores one tournament evaluation context
- `models/avatar_match_result.py`
  - Stores one avatar’s predicted + actual result inside a tournament run
- `models/avatar_policy_state.py`
  - Stores current state, weights, cooldown, confidence
- `models/avatar_promotion_event.py`
  - Stores promotion / demotion / rollback state changes
- `models/avatar_guardrail_event.py`
  - Stores continuity/brand/retention/policy guardrail incidents

### Schemas
- `schemas/avatar_tournament.py`
  - Request/response contracts for ranking, run creation, result views
- `schemas/avatar_governance.py`
  - Policy state views, promotion decisions, action payloads
- `schemas/avatar_selection_debug.py`
  - Fine-grained score breakdown and explanation payload

### Avatar services
- `services/avatar/avatar_tournament_engine.py`
  - Candidate collection, scoring, exploit/explore selection, persistence
- `services/avatar/avatar_governance_engine.py`
  - Promotion/demotion/cooldown/rollback logic from actual outcomes
- `services/avatar/avatar_policy_engine.py`
  - Stateful policy rules and threshold config
- `services/avatar/avatar_weight_engine.py`
  - Final ranking weight calculation
- `services/avatar/avatar_pair_learning_engine.py`
  - Learns avatar × template × topic × platform fit
- `services/avatar/avatar_rollback_service.py`
  - Selects stable fallback avatar and applies rollback actions
- `services/avatar/avatar_selection_explainer.py`
  - Human/debug readable explanation lines for why a candidate won or lost

### Modified brain/publish/render services
- `services/brain/brain_decision_engine.py`
  - Inject tournament before render selection
- `services/brain/brain_feedback_service.py`
  - Push actual outcomes into governance engine
- `services/publish/publish_scheduler.py`
  - Respect cooldown/priority/exploration quotas
- `services/render/execution_bridge_service.py`
  - Inject avatar policy context into render payload
- `services/render/render_execution.py`
  - Persist render-time avatar metadata and selection reason

## Notes
- This pack assumes existing avatar files from your prior patch already exist:
  - `schemas/avatar_system.py`
  - `models/avatar_profile.py`
  - `models/avatar_performance.py`
  - `services/avatar/avatar_registry.py`
  - `services/avatar/avatar_identity_engine.py`
  - `services/avatar/avatar_memory_service.py`
  - `services/avatar/avatar_voice_engine.py`
  - `services/avatar/avatar_continuity_engine.py`
  - `services/avatar/avatar_scene_mapper.py`
  - `services/avatar/avatar_scorecard.py`
  - `services/avatar/avatar_pair_optimizer.py`
- This patch is additive-first and intentionally does not replace the render core.
