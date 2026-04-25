"""Unified Rebuild Decision Engine.

Single entry-point that combines:
  - DependencyService (affected scenes + reasons)
  - RebuildPolicyEngine (required / optional / skip classification)
  - RebuildStrategyOptimizer (cheapest safe strategy)
  - ExecutionBudgetGuard (budget enforcement, downgrade/block)
  - BudgetAwareResponseBuilder-compatible output

Produces a single canonical decision payload that the API returns directly to
the frontend and that :class:`~app.render.execution.approved_rebuild_executor.ApprovedRebuildExecutor`
consumes.

Output schema::

    {
        "selected_strategy": "safe_minimum",
        "decision": "allow | downgrade | block",
        "reason_summary": "...",
        "budget_policy": "cheap | balanced | quality | emergency",
        "estimated_cost": {},
        "estimated_time": {},
        "affected_scenes": [],
        "mandatory_scenes": [],
        "optional_scenes": [],
        "skipped_scenes": [],
        "warnings": []
    }
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.render.dependency.dependency_service import DependencyService
from app.render.manifest.manifest_service import ManifestService
from app.render.reassembly.optimizer.budget_policy_presets import resolve_budget_policy
from app.render.reassembly.optimizer.execution_budget_guard import ExecutionBudgetGuard
from app.render.reassembly.optimizer.rebuild_cost_estimator import RebuildCostEstimator
from app.render.reassembly.optimizer.rebuild_strategy_optimizer import RebuildStrategyOptimizer
from app.render.reassembly.policy.rebuild_policy_engine import RebuildPolicyEngine


class UnifiedRebuildDecisionEngine:
    """Pipeline: Dependency → Policy → Strategy → Budget → Decision payload.

    All collaborators can be overridden in tests via constructor injection.
    """

    def __init__(
        self,
        manifest_base_dir: str | None = None,
        dependency_base_dir: str | None = None,
    ) -> None:
        self._manifest = ManifestService(base_dir=manifest_base_dir)
        self._dependency = DependencyService(
            manifest_base_dir=manifest_base_dir,
            dependency_base_dir=dependency_base_dir,
        )
        self._policy = RebuildPolicyEngine()
        self._optimizer = RebuildStrategyOptimizer()
        self._budget_guard = ExecutionBudgetGuard()
        self._cost_estimator = RebuildCostEstimator()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def decide(
        self,
        project_id: str,
        episode_id: str,
        changed_scene_id: str,
        change_type: str = "subtitle",
        budget_policy: Optional[str] = "balanced",
        force_full_rebuild: bool = False,
        force_quality_rebuild: bool = False,
        include_optional_rebuilds: bool = False,
        has_timeline_drift: bool = False,
        affected_range_scene_ids: Optional[List[str]] = None,
        # Budget override – these take precedence over the policy preset when provided
        max_rebuild_cost: Optional[float] = None,
        max_rebuild_time_sec: Optional[float] = None,
        allow_budget_downgrade: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Produce a single, self-contained rebuild decision payload.

        Args:
            project_id: Owning project.
            episode_id: Target episode.
            changed_scene_id: The scene whose content changed.
            change_type: Category of the change (voice, subtitle, avatar…).
            budget_policy: Named preset – cheap / balanced / quality / emergency.
            force_full_rebuild: Skip optimisation and always choose full_rebuild.
            force_quality_rebuild: Promote optional scenes to required.
            include_optional_rebuilds: Include optional scenes in rebuild scope.
            has_timeline_drift: Whether the changed scene has a duration drift.
            affected_range_scene_ids: Pre-computed affected range (optional).
            max_rebuild_cost: Override max cost from budget preset.
            max_rebuild_time_sec: Override max time from budget preset.
            allow_budget_downgrade: Override downgrade flag from budget preset.

        Returns:
            Decision payload dict (see module docstring).
        """
        # ── 1. Load manifests ────────────────────────────────────────
        all_manifests = self._manifest.list_episode(project_id, episode_id)
        if not all_manifests:
            return self._empty_decision(
                project_id, episode_id, changed_scene_id, budget_policy,
                warning="No manifests found for episode",
            )

        # ── 2. Dependency reasons ────────────────────────────────────
        reasons_by_scene = self._dependency.affected_scenes_with_reasons(
            project_id=project_id,
            episode_id=episode_id,
            changed_scene_id=changed_scene_id,
            change_type=change_type,
        )

        affected_scene_ids: List[str] = list(reasons_by_scene.keys())

        # ── 3. Policy classification ────────────────────────────────
        required_ids: List[str] = []
        optional_ids: List[str] = []
        skipped_ids: List[str] = []
        policy_details: List[Dict[str, Any]] = []

        for scene_manifest in all_manifests:
            sid = scene_manifest["scene_id"]
            reasons = reasons_by_scene.get(sid, [])
            result = self._policy.classify_scene(
                scene_id=sid,
                reasons=reasons,
                force_quality=force_quality_rebuild,
            )
            policy_details.append(result)
            if result["decision"] == "required":
                required_ids.append(sid)
            elif result["decision"] == "optional":
                optional_ids.append(sid)
            else:
                skipped_ids.append(sid)

        # ── 4. Strategy optimisation ────────────────────────────────
        optimisation = self._optimizer.choose_strategy(
            all_manifests=all_manifests,
            changed_scene_id=changed_scene_id,
            required_scene_ids=required_ids,
            optional_scene_ids=optional_ids,
            affected_range_scene_ids=affected_range_scene_ids or [],
            change_type=change_type,
            has_timeline_drift=has_timeline_drift,
            force_full_rebuild=force_full_rebuild,
            include_optional=include_optional_rebuilds,
        )

        chosen = optimisation["chosen_strategy"]

        # ── 5. Budget resolution ─────────────────────────────────────
        preset = resolve_budget_policy(budget_policy)
        effective_max_cost: float = (
            max_rebuild_cost
            if max_rebuild_cost is not None
            else float(preset["max_rebuild_cost"])
        )
        effective_max_time: float = (
            max_rebuild_time_sec
            if max_rebuild_time_sec is not None
            else float(preset["max_rebuild_time_sec"])
        )
        effective_downgrade: bool = (
            allow_budget_downgrade
            if allow_budget_downgrade is not None
            else bool(preset["allow_budget_downgrade"])
        )

        budget_result = self._budget_guard.enforce(
            optimization=optimisation,
            max_cost=effective_max_cost,
            max_time_sec=effective_max_time,
            allow_downgrade=effective_downgrade,
        )

        # ── 6. Cost estimate for chosen strategy ────────────────────
        final_strategy = budget_result["chosen_strategy"]
        rebuild_scene_ids: List[str] = final_strategy.get("scene_ids", required_ids)

        total_cost = 0.0
        total_time = 0.0
        scene_cost_details: List[Dict[str, Any]] = []
        manifest_by_id = {m["scene_id"]: m for m in all_manifests}

        for sid in rebuild_scene_ids:
            m = manifest_by_id.get(sid, {"scene_id": sid})
            est = self._cost_estimator.estimate_scene(m, change_type)
            total_cost += est["estimated_cost"]
            total_time += est["estimated_time_sec"]
            scene_cost_details.append(est)

        # ── 7. Build warnings ────────────────────────────────────────
        warnings: List[str] = []
        action = budget_result.get("action", "allow")
        if action == "downgrade":
            warnings.append(
                f"Budget exceeded – strategy downgraded from "
                f"'{chosen.get('strategy')}' to '{final_strategy.get('strategy')}'."
            )
        if action == "block":
            warnings.append(
                f"Rebuild blocked: estimated cost {chosen.get('estimated_cost', 0):.1f} "
                f"exceeds budget {effective_max_cost:.1f} and downgrade is disabled."
            )
        if has_timeline_drift:
            warnings.append("Timeline drift detected — all following scenes will be rebuilt.")

        # ── 8. Reason summary ────────────────────────────────────────
        reason_summary = self._build_reason_summary(
            changed_scene_id=changed_scene_id,
            change_type=change_type,
            required_count=len(required_ids),
            optional_count=len(optional_ids),
            action=action,
            strategy_name=final_strategy.get("strategy", "unknown"),
        )

        return {
            "project_id": project_id,
            "episode_id": episode_id,
            "changed_scene_id": changed_scene_id,
            "change_type": change_type,
            "selected_strategy": final_strategy.get("strategy", "unknown"),
            "decision": action,
            "reason_summary": reason_summary,
            "budget_policy": preset["policy"],
            "estimated_cost": {
                "total": round(total_cost, 4),
                "by_scene": scene_cost_details,
                "budget_limit": effective_max_cost,
            },
            "estimated_time": {
                "total_sec": round(total_time, 2),
                "time_limit_sec": effective_max_time,
            },
            "affected_scenes": affected_scene_ids,
            "mandatory_scenes": required_ids,
            "optional_scenes": optional_ids,
            "skipped_scenes": skipped_ids,
            "rebuild_scene_ids": rebuild_scene_ids,
            "has_timeline_drift": has_timeline_drift,
            "policy_details": policy_details,
            "budget_guard_result": budget_result,
            "optimisation_result": optimisation,
            "warnings": warnings,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_reason_summary(
        self,
        changed_scene_id: str,
        change_type: str,
        required_count: int,
        optional_count: int,
        action: str,
        strategy_name: str,
    ) -> str:
        action_map = {
            "allow": "Rebuild approved",
            "downgrade": "Rebuild downgraded (budget)",
            "block": "Rebuild blocked (budget exceeded)",
        }
        label = action_map.get(action, "Rebuild decision")
        return (
            f"{label}: scene '{changed_scene_id}' changed ({change_type}). "
            f"{required_count} scene(s) required, {optional_count} optional. "
            f"Strategy: {strategy_name}."
        )

    def _empty_decision(
        self,
        project_id: str,
        episode_id: str,
        changed_scene_id: str,
        budget_policy: Optional[str],
        warning: str = "",
    ) -> Dict[str, Any]:
        preset = resolve_budget_policy(budget_policy)
        return {
            "project_id": project_id,
            "episode_id": episode_id,
            "changed_scene_id": changed_scene_id,
            "change_type": "unknown",
            "selected_strategy": "none",
            "decision": "block",
            "reason_summary": warning or "No episode data available.",
            "budget_policy": preset["policy"],
            "estimated_cost": {"total": 0.0, "by_scene": [], "budget_limit": 0.0},
            "estimated_time": {"total_sec": 0.0, "time_limit_sec": 0.0},
            "affected_scenes": [],
            "mandatory_scenes": [],
            "optional_scenes": [],
            "skipped_scenes": [],
            "rebuild_scene_ids": [],
            "has_timeline_drift": False,
            "policy_details": [],
            "budget_guard_result": {},
            "optimisation_result": {},
            "warnings": [warning] if warning else [],
        }
