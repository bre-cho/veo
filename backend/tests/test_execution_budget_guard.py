"""Tests for ExecutionBudgetGuard — allow / downgrade / block decisions."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.render.reassembly.optimizer.execution_budget_guard import ExecutionBudgetGuard


def _make_strategy(strategy: str, cost: float, time_sec: float, safe: bool = True) -> dict:
    return {
        "strategy": strategy,
        "scene_ids": ["s1"],
        "estimated_cost": cost,
        "estimated_time_sec": time_sec,
        "safe": safe,
        "reason": "test",
    }


def test_allows_strategy_within_budget():
    guard = ExecutionBudgetGuard()
    result = guard.enforce(
        {
            "chosen_strategy": _make_strategy("dependency_set", 20, 200),
            "candidates": [],
        },
        max_cost=30,
        max_time_sec=300,
    )
    assert result["allowed"] is True
    assert result["action"] == "allow"


def test_blocks_when_over_budget_and_no_downgrade():
    guard = ExecutionBudgetGuard()
    result = guard.enforce(
        {
            "chosen_strategy": _make_strategy("full_rebuild", 100, 1200),
            "candidates": [],
        },
        max_cost=30,
        max_time_sec=300,
        allow_downgrade=False,
    )
    assert result["allowed"] is False
    assert result["action"] == "block"
    assert "downgrade is disabled" in result["reason"]


def test_downgrades_to_safe_budget_candidate():
    guard = ExecutionBudgetGuard()
    result = guard.enforce(
        {
            "chosen_strategy": _make_strategy("full_rebuild", 100, 1200),
            "candidates": [
                _make_strategy("dependency_set", 20, 200),
            ],
        },
        max_cost=30,
        max_time_sec=300,
    )
    assert result["allowed"] is True
    assert result["action"] == "downgrade"
    assert result["chosen_strategy"]["strategy"] == "dependency_set"
    assert "original_strategy" in result


def test_blocks_when_no_safe_budget_candidate():
    guard = ExecutionBudgetGuard()
    result = guard.enforce(
        {
            "chosen_strategy": _make_strategy("full_rebuild", 100, 1200),
            "candidates": [
                _make_strategy("dependency_set", 40, 500),  # over budget
            ],
        },
        max_cost=30,
        max_time_sec=300,
    )
    assert result["allowed"] is False
    assert result["action"] == "block"
    assert "no safe strategy fits" in result["reason"]


def test_picks_cheapest_downgrade_when_multiple_candidates():
    guard = ExecutionBudgetGuard()
    result = guard.enforce(
        {
            "chosen_strategy": _make_strategy("full_rebuild", 100, 1200),
            "candidates": [
                _make_strategy("dependency_set", 20, 200),
                _make_strategy("changed_only", 5, 50),
            ],
        },
        max_cost=30,
        max_time_sec=300,
    )
    assert result["allowed"] is True
    assert result["chosen_strategy"]["strategy"] == "changed_only"


def test_unsafe_candidates_not_eligible_for_downgrade():
    guard = ExecutionBudgetGuard()
    result = guard.enforce(
        {
            "chosen_strategy": _make_strategy("full_rebuild", 100, 1200),
            "candidates": [
                _make_strategy("changed_only", 5, 50, safe=False),
            ],
        },
        max_cost=30,
        max_time_sec=300,
    )
    assert result["allowed"] is False
    assert result["action"] == "block"


def test_default_budget_limits_allow_moderate_strategy():
    guard = ExecutionBudgetGuard()
    result = guard.enforce(
        {
            "chosen_strategy": _make_strategy("dependency_set", 30, 300),
            "candidates": [],
        }
        # use defaults: max_cost=50, max_time_sec=600
    )
    assert result["allowed"] is True
    assert result["action"] == "allow"


def test_exactly_at_budget_boundary_is_allowed():
    guard = ExecutionBudgetGuard()
    result = guard.enforce(
        {
            "chosen_strategy": _make_strategy("dependency_set", 30.0, 300.0),
            "candidates": [],
        },
        max_cost=30.0,
        max_time_sec=300.0,
    )
    assert result["allowed"] is True
