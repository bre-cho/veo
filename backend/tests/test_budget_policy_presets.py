"""Tests for budget policy preset resolution."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.render.reassembly.optimizer.budget_policy_presets import (
    BUDGET_POLICY_PRESETS,
    resolve_budget_policy,
)


def test_default_policy_is_balanced():
    policy = resolve_budget_policy(None)
    assert policy["policy"] == "balanced"


def test_empty_string_falls_back_to_balanced():
    policy = resolve_budget_policy("")
    assert policy["policy"] == "balanced"


def test_unknown_policy_falls_back_to_balanced():
    policy = resolve_budget_policy("unknown_policy")
    assert policy["policy"] == "balanced"


def test_all_presets_resolve():
    for name in ("cheap", "balanced", "quality", "emergency"):
        policy = resolve_budget_policy(name)
        assert policy["policy"] == name
        assert "max_rebuild_cost" in policy
        assert "max_rebuild_time_sec" in policy
        assert "allow_budget_downgrade" in policy
        assert "include_optional_rebuilds" in policy


def test_cheap_policy_is_stricter_than_quality():
    cheap = resolve_budget_policy("cheap")
    quality = resolve_budget_policy("quality")
    assert cheap["max_rebuild_cost"] < quality["max_rebuild_cost"]
    assert cheap["max_rebuild_time_sec"] < quality["max_rebuild_time_sec"]
    assert cheap["include_optional_rebuilds"] is False
    assert quality["include_optional_rebuilds"] is True


def test_emergency_is_most_restrictive():
    emergency = resolve_budget_policy("emergency")
    cheap = resolve_budget_policy("cheap")
    assert emergency["max_rebuild_cost"] < cheap["max_rebuild_cost"]
    assert emergency["max_rebuild_time_sec"] < cheap["max_rebuild_time_sec"]


def test_quality_disables_downgrade():
    quality = resolve_budget_policy("quality")
    assert quality["allow_budget_downgrade"] is False


def test_cheap_and_balanced_allow_downgrade():
    for name in ("cheap", "balanced", "emergency"):
        policy = resolve_budget_policy(name)
        assert policy["allow_budget_downgrade"] is True, f"{name} should allow downgrade"


def test_case_insensitive_lookup():
    policy = resolve_budget_policy("CHEAP")
    assert policy["policy"] == "cheap"

    policy = resolve_budget_policy("Quality")
    assert policy["policy"] == "quality"
