# service_wiring.md

## Goal
Wire avatar tournament and governance into the existing system with the least-risk additive pattern:
- score before render
- observe after publish
- adjust future selection without rewriting render core

---

## 1) Dependency flow

```txt
avatar_registry
    + avatar_scorecard
    + avatar_pair_optimizer
    + avatar_continuity_engine
    + avatar_policy_engine
    + avatar_weight_engine
    -> avatar_tournament_engine
    -> brain_decision_engine
    -> execution_bridge_service / render_execution

publish outcome / analytics
    -> brain_feedback_service
    -> avatar_governance_engine
    -> avatar_policy_state + promotion/guardrail events
    -> publish_scheduler (next cycle)
```

---

## 2) Service responsibilities

### `services/avatar/avatar_tournament_engine.py`
Inputs:
- workspace/project context
- topic_signature
- template_family
- platform
- candidate avatar ids

Calls:
- `avatar_registry.get_candidates(...)`
- `avatar_scorecard.build_avatar_scorecard(...)`
- `avatar_pair_optimizer.get_pair_score(...)`
- `avatar_continuity_engine.build_continuity_context(...)`
- `avatar_policy_engine.get_state(...)`
- `avatar_weight_engine.build_final_rank(...)`
- `avatar_selection_explainer.explain(...)`

Outputs:
- ranked candidates
- selected avatar id
- selection mode: exploit/explore/forced_test
- tournament persistence payload

### `services/avatar/avatar_governance_engine.py`
Inputs:
- actual metrics from publish/feedback
- avatar_id
- tournament_run_id optional
- context

Calls:
- `avatar_policy_engine.get_state(...)`
- `avatar_policy_engine.evaluate_thresholds(...)`
- `avatar_rollback_service.choose_fallback(...)` when needed

Outputs:
- updated state
- promotion/demotion/cooldown/rollback event
- guardrail event when triggered

### `services/avatar/avatar_policy_engine.py`
Owns:
- thresholds
- transition rules
- cooldown windows
- exploration floors
- decay rules

Suggested config surface:
```python
AVATAR_POLICY = {
    "priority_min_valid_outcomes": 3,
    "cooldown_retention_drop_threshold": -0.15,
    "rollback_retention_drop_threshold": -0.20,
    "min_exploration_ratio": 0.10,
    "max_priority_share": 0.80,
}
```

### `services/avatar/avatar_weight_engine.py`
Computes final score:
```txt
final_rank_score =
base_score
+ pair_bonus
+ continuity_bonus
+ recent_win_bonus
+ exploration_bonus
- governance_penalty
- risk_penalty
- decay_penalty
```

### `services/avatar/avatar_pair_learning_engine.py`
Reads `avatar_match_results` and learns:
- avatar × template family
- avatar × topic signature
- avatar × platform

Returns:
- pair_bonus
- pair_confidence
- history_count

### `services/avatar/avatar_rollback_service.py`
Used only when:
- retention crash
- continuity hard break
- repeated failure under rollout

Returns:
- fallback avatar id
- rollback action payload
- cooldown duration

### `services/avatar/avatar_selection_explainer.py`
Produces:
- explanation lines for debug UI/API
- “why selected” payload for manifest/render metadata

---

## 3) Brain wiring

### `services/brain/brain_decision_engine.py`
Inject this before final preview/render decision is built:

```python
avatar_selection = avatar_tournament_engine.run_tournament(
    workspace_id=workspace_id,
    project_id=project_id,
    topic_signature=topic_signature,
    template_family=template_family,
    platform=platform,
    candidate_avatar_ids=candidate_avatar_ids,
    baseline_avatar_id=baseline_avatar_id,
    context=decision_context,
)

decision.avatar_id = avatar_selection.selected_avatar_id
decision.avatar_selection_mode = avatar_selection.selection_mode
decision.avatar_selection_debug = avatar_selection.explanation
decision.avatar_tournament_run_id = avatar_selection.tournament_run_id
```

Fallback rule:
- if tournament cannot score enough candidates, use current stable avatar or existing decision path
- never hard-fail render just because tournament layer is degraded

### `services/brain/brain_feedback_service.py`
After actual publish metrics are available:

```python
governance_result = avatar_governance_engine.evaluate_avatar_outcome(
    avatar_id=avatar_id,
    tournament_run_id=tournament_run_id,
    metrics=publish_metrics,
    context=feedback_context,
)
```

Write back:
- `avatar_policy_states`
- `avatar_promotion_events`
- `avatar_guardrail_events`
- optional update of `avatar_match_results.actual_*`

---

## 4) Publish wiring

### `services/publish/publish_scheduler.py`
When building candidate queue:
- respect `cooldown_until`
- prioritize `state=priority`
- keep exploration floor alive
- cap repeated dominance from one avatar

Suggested selection rules:
1. Exclude blocked/retired
2. Skip cooldown unless manual override
3. Reserve 10–20% exploration slots
4. Prefer stable pair winners, not only raw avatar winners

Pseudo:
```python
if policy.state in {"blocked", "retired"}:
    skip()
elif policy.state == "cooldown" and not manual_override:
    skip()
elif exploration_slot_open:
    consider(candidate_pool_with_exploration_weight)
else:
    consider(priority_pool_with_governance_rules)
```

---

## 5) Render wiring

### `services/render/execution_bridge_service.py`
Inject avatar context into render payload:

```python
render_context["avatar_id"] = decision.avatar_id
render_context["avatar_tournament_run_id"] = decision.avatar_tournament_run_id
render_context["avatar_selection_mode"] = decision.avatar_selection_mode
render_context["avatar_selection_reason"] = decision.avatar_selection_debug
render_context["avatar_policy_state"] = avatar_policy_state.state
render_context["avatar_continuity_payload"] = continuity_payload
```

### `services/render/render_execution.py`
Persist metadata for traceability:
- avatar_id
- tournament_run_id
- selection mode
- selection reason
- policy state snapshot

Important:
- do not alter provider adapter contracts unless they already support metadata passthrough
- if metadata fields are unsupported by providers, keep them in internal execution manifest only

---

## 6) API wiring

### `api/avatar_tournament.py`
Suggested routes:
- `POST /api/v1/avatar/tournament/run`
- `GET /api/v1/avatar/tournament/{run_id}`

Route → Service:
```txt
route -> avatar_tournament_engine
route -> avatar_selection_explainer (if you separate explanation reconstruction)
```

### `api/avatar_governance.py`
Suggested routes:
- `GET /api/v1/avatar/governance/state/{avatar_id}`
- `POST /api/v1/avatar/governance/recalculate/{avatar_id}`
- `POST /api/v1/avatar/governance/rollback/{avatar_id}`

Route → Service:
```txt
route -> avatar_policy_engine
route -> avatar_governance_engine
route -> avatar_rollback_service
```

---

## 7) Persistence update points

### On tournament run start
Create `avatar_tournament_runs` row with:
- context
- candidate pool
- selection mode default pending/running

### On tournament completion
Update:
- selected avatar
- ranked results in `avatar_match_results`
- completed timestamps

### On publish outcome
Update winning match row:
- actual_ctr
- actual_retention
- actual_watch_time
- actual_conversion
- fitness_score
- result_label

### On policy transition
Insert:
- `avatar_promotion_events`
- optional `avatar_guardrail_events`

---

## 8) Safety / degradation strategy

This layer must be soft-fail:
- if pair-learning is empty, score without pair bonus
- if policy state missing, initialize `candidate`
- if governance calculation fails, do not block publish; log event and keep last known policy
- if tournament service unavailable, use current stable avatar path

Recommended guard:
```python
try:
    avatar_selection = avatar_tournament_engine.run_tournament(...)
except Exception:
    logger.exception("avatar_tournament_failed")
    avatar_selection = stable_avatar_fallback(...)
```

---

## 9) Suggested tests

### Unit
- weight calculation
- policy state transition
- rollback decision
- exploration floor enforcement

### Integration
- tournament run persists results
- feedback updates policy state
- scheduler skips cooldown avatars
- render manifest contains avatar metadata

### E2E smoke
1. Create avatars
2. Run tournament
3. Select avatar
4. Render with selected avatar
5. Feed poor retention
6. Observe cooldown/rollback
7. Run next tournament and confirm changed priority

---

## 10) Non-goals in this patch
- No ML model requirement
- No provider API rewrite
- No hard dependency on external analytics stack
- No UI implementation requirement beyond API readiness
