from __future__ import annotations

from typing import Any, Dict, List, Optional


class BudgetAwareResponseBuilder:
    """Build a frontend-friendly summary of the budget enforcement decision.

    Combines the raw optimizer output, the budget guard decision, and the
    resolved policy preset into a single flat dict that is easy to map to
    UI badges, cost labels, and strategy dropdowns.
    """

    def build(
        self,
        optimization: Dict[str, Any],
        budget_decision: Dict[str, Any],
        budget_policy: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build the budget API report.

        Args:
            optimization: Full output of
                :meth:`~RebuildStrategyOptimizer.choose_strategy`.
            budget_decision: Output of
                :meth:`~ExecutionBudgetGuard.enforce`.
            budget_policy: Resolved policy dict from
                :func:`~resolve_budget_policy`.

        Returns:
            Dict suitable for inclusion in the smart-reassembly API response.
        """
        chosen: Dict[str, Any] = budget_decision.get("chosen_strategy", {})
        original: Optional[Dict[str, Any]] = budget_decision.get("original_strategy")
        budget_limits: Dict[str, Any] = budget_decision.get("budget", {})

        max_cost = float(budget_limits.get("max_cost", 0.0))
        max_time_sec = float(budget_limits.get("max_time_sec", 0.0))

        candidates: List[Dict[str, Any]] = optimization.get("candidates", [])

        return {
            "budget_status": budget_decision.get("action", "unknown"),
            "budget_allowed": budget_decision.get("allowed", False),
            "budget_reason": budget_decision.get("reason", ""),
            "budget_policy_name": budget_policy.get("policy", "balanced"),
            "budget_limits": {
                "max_cost": max_cost,
                "max_time_sec": max_time_sec,
            },
            "selected_strategy": {
                "name": chosen.get("strategy"),
                "scene_ids": chosen.get("scene_ids", []),
                "estimated_cost": chosen.get("estimated_cost", 0.0),
                "estimated_time_sec": chosen.get("estimated_time_sec", 0.0),
                "safe": chosen.get("safe", False),
                "reason": chosen.get("reason", ""),
            },
            "original_strategy": {
                "name": original.get("strategy") if original else None,
                "estimated_cost": original.get("estimated_cost") if original else None,
                "estimated_time_sec": original.get("estimated_time_sec") if original else None,
                "reason": original.get("reason") if original else None,
            },
            "strategy_candidates": [
                {
                    "name": item.get("strategy"),
                    "scene_count": len(item.get("scene_ids", [])),
                    "estimated_cost": item.get("estimated_cost", 0.0),
                    "estimated_time_sec": item.get("estimated_time_sec", 0.0),
                    "safe": item.get("safe", False),
                    "reason": item.get("reason", ""),
                    "within_budget": (
                        float(item.get("estimated_cost", 0.0)) <= max_cost
                        and float(item.get("estimated_time_sec", 0.0)) <= max_time_sec
                    ),
                }
                for item in candidates
            ],
        }
