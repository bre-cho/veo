from __future__ import annotations

from typing import Any, Dict, List, Optional


class ExecutionBudgetGuard:
    """Enforce cost/time budget limits on a chosen rebuild strategy.

    When the chosen strategy exceeds the budget the guard either:
    * **downgrades** to the cheapest safe candidate that fits (when
      ``allow_downgrade=True``), or
    * **blocks** the rebuild (when ``allow_downgrade=False`` or no
      in-budget safe candidate exists).
    """

    DEFAULT_MAX_COST = 50.0
    DEFAULT_MAX_TIME_SEC = 600.0

    def enforce(
        self,
        optimization: Dict[str, Any],
        max_cost: Optional[float] = None,
        max_time_sec: Optional[float] = None,
        allow_downgrade: bool = True,
    ) -> Dict[str, Any]:
        """Enforce the budget against the optimizer output.

        Args:
            optimization: Output of :meth:`RebuildStrategyOptimizer.choose_strategy`,
                containing ``chosen_strategy`` and ``candidates``.
            max_cost: Maximum allowed estimated cost.  Defaults to
                :attr:`DEFAULT_MAX_COST`.
            max_time_sec: Maximum allowed estimated time in seconds.  Defaults
                to :attr:`DEFAULT_MAX_TIME_SEC`.
            allow_downgrade: When ``True`` and the chosen strategy exceeds the
                budget, try to downgrade to the cheapest safe in-budget
                candidate.  When ``False``, block the rebuild immediately.

        Returns:
            Dict with ``allowed``, ``action`` (``"allow"``, ``"downgrade"``,
            or ``"block"``), ``chosen_strategy``, and ``budget`` metadata.
        """
        max_cost = self.DEFAULT_MAX_COST if max_cost is None else float(max_cost)
        max_time_sec = self.DEFAULT_MAX_TIME_SEC if max_time_sec is None else float(max_time_sec)

        chosen = optimization["chosen_strategy"]
        candidates: List[Dict[str, Any]] = optimization.get("candidates", [])

        budget = {"max_cost": max_cost, "max_time_sec": max_time_sec}

        if self._within_budget(chosen, max_cost, max_time_sec):
            return {
                "allowed": True,
                "action": "allow",
                "chosen_strategy": chosen,
                "budget": budget,
                "reason": "chosen strategy is within execution budget",
            }

        if not allow_downgrade:
            return {
                "allowed": False,
                "action": "block",
                "chosen_strategy": chosen,
                "budget": budget,
                "reason": "chosen strategy exceeds execution budget and downgrade is disabled",
            }

        safe_budget_candidates = [
            item for item in candidates
            if item.get("safe") is True
            and self._within_budget(item, max_cost, max_time_sec)
        ]

        if safe_budget_candidates:
            downgraded = min(
                safe_budget_candidates,
                key=lambda x: (
                    float(x.get("estimated_cost", 0.0)),
                    float(x.get("estimated_time_sec", 0.0)),
                ),
            )
            return {
                "allowed": True,
                "action": "downgrade",
                "chosen_strategy": downgraded,
                "original_strategy": chosen,
                "budget": budget,
                "reason": (
                    "original strategy exceeded budget; "
                    "downgraded to cheapest safe in-budget strategy"
                ),
            }

        return {
            "allowed": False,
            "action": "block",
            "chosen_strategy": chosen,
            "budget": budget,
            "reason": "no safe strategy fits execution budget",
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _within_budget(
        self,
        strategy: Dict[str, Any],
        max_cost: float,
        max_time_sec: float,
    ) -> bool:
        return (
            float(strategy.get("estimated_cost", 0.0)) <= max_cost
            and float(strategy.get("estimated_time_sec", 0.0)) <= max_time_sec
        )
