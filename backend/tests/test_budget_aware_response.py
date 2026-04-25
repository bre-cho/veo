"""Tests for BudgetAwareResponseBuilder."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.render.reassembly.budget_response_builder import BudgetAwareResponseBuilder


def _make_strategy(name: str, cost: float, time_sec: float, safe: bool = True, scene_ids=None) -> dict:
    return {
        "strategy": name,
        "scene_ids": scene_ids or ["s1"],
        "estimated_cost": cost,
        "estimated_time_sec": time_sec,
        "safe": safe,
        "reason": f"{name} reason",
    }


def test_budget_response_for_downgrade():
    builder = BudgetAwareResponseBuilder()

    report = builder.build(
        optimization={
            "candidates": [
                _make_strategy("changed_only", 10, 80),
            ]
        },
        budget_decision={
            "allowed": True,
            "action": "downgrade",
            "reason": "over budget",
            "budget": {"max_cost": 15, "max_time_sec": 100},
            "chosen_strategy": _make_strategy("changed_only", 10, 80),
            "original_strategy": _make_strategy("dependency_set", 30, 200),
        },
        budget_policy={"policy": "cheap"},
    )

    assert report["budget_status"] == "downgrade"
    assert report["budget_allowed"] is True
    assert report["selected_strategy"]["name"] == "changed_only"
    assert report["original_strategy"]["name"] == "dependency_set"
    assert report["strategy_candidates"][0]["within_budget"] is True
    assert report["budget_policy_name"] == "cheap"


def test_budget_response_for_allow():
    builder = BudgetAwareResponseBuilder()

    report = builder.build(
        optimization={"candidates": []},
        budget_decision={
            "allowed": True,
            "action": "allow",
            "reason": "within budget",
            "budget": {"max_cost": 50, "max_time_sec": 600},
            "chosen_strategy": _make_strategy("dependency_set", 20, 200),
        },
        budget_policy={"policy": "balanced"},
    )

    assert report["budget_status"] == "allow"
    assert report["budget_allowed"] is True
    assert report["original_strategy"]["name"] is None
    assert report["budget_policy_name"] == "balanced"


def test_budget_response_for_block():
    builder = BudgetAwareResponseBuilder()

    report = builder.build(
        optimization={"candidates": []},
        budget_decision={
            "allowed": False,
            "action": "block",
            "reason": "no safe strategy fits budget",
            "budget": {"max_cost": 5, "max_time_sec": 30},
            "chosen_strategy": _make_strategy("full_rebuild", 100, 1200),
        },
        budget_policy={"policy": "emergency"},
    )

    assert report["budget_status"] == "block"
    assert report["budget_allowed"] is False
    assert report["budget_policy_name"] == "emergency"


def test_within_budget_flag_on_candidates():
    builder = BudgetAwareResponseBuilder()

    report = builder.build(
        optimization={
            "candidates": [
                _make_strategy("changed_only", 5, 40),    # within 15 / 180
                _make_strategy("dependency_set", 20, 200), # over cost
                _make_strategy("full_rebuild", 100, 1200), # way over
            ]
        },
        budget_decision={
            "allowed": True,
            "action": "allow",
            "reason": "ok",
            "budget": {"max_cost": 15, "max_time_sec": 180},
            "chosen_strategy": _make_strategy("changed_only", 5, 40),
        },
        budget_policy={"policy": "cheap"},
    )

    within = [c["within_budget"] for c in report["strategy_candidates"]]
    assert within == [True, False, False]


def test_budget_limits_in_response():
    builder = BudgetAwareResponseBuilder()

    report = builder.build(
        optimization={"candidates": []},
        budget_decision={
            "allowed": True,
            "action": "allow",
            "reason": "ok",
            "budget": {"max_cost": 30.0, "max_time_sec": 300.0},
            "chosen_strategy": _make_strategy("changed_only", 10, 80),
        },
        budget_policy={"policy": "balanced"},
    )

    assert report["budget_limits"]["max_cost"] == 30.0
    assert report["budget_limits"]["max_time_sec"] == 300.0
