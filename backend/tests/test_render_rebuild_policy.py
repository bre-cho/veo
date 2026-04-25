"""Tests for the RebuildPolicyEngine (mandatory / optional / skip decisions)."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the backend package is importable when running pytest from the repo root.
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.render.reassembly.rebuild_policy_engine import RebuildPolicyEngine


def test_self_change_is_mandatory():
    engine = RebuildPolicyEngine()
    report = engine.classify_scene([
        {"dependency_type": "self", "strength": 1.0}
    ])
    assert report["policy"] == "mandatory"


def test_timeline_type_is_mandatory():
    engine = RebuildPolicyEngine()
    report = engine.classify_scene([
        {"dependency_type": "timeline", "strength": 0.4}
    ])
    assert report["policy"] == "mandatory"


def test_strong_dependency_is_mandatory():
    engine = RebuildPolicyEngine()
    report = engine.classify_scene([
        {"dependency_type": "avatar", "strength": 0.9}
    ])
    assert report["policy"] == "mandatory"


def test_medium_dependency_is_optional():
    engine = RebuildPolicyEngine()
    report = engine.classify_scene([
        {"dependency_type": "style", "strength": 0.6}
    ])
    assert report["policy"] == "optional"


def test_weak_dependency_is_skipped():
    engine = RebuildPolicyEngine()
    report = engine.classify_scene([
        {"dependency_type": "continuity", "strength": 0.2}
    ])
    assert report["policy"] == "skip"


def test_empty_reasons_returns_skip():
    engine = RebuildPolicyEngine()
    report = engine.classify_scene([])
    assert report["policy"] == "skip"
    assert report["max_strength"] == 0.0


def test_classify_all_groups_correctly():
    engine = RebuildPolicyEngine()
    rebuild_reasons = {
        "s1": [{"dependency_type": "self", "strength": 1.0}],
        "s2": [{"dependency_type": "avatar", "strength": 0.6}],
        "s3": [{"dependency_type": "continuity", "strength": 0.3}],
    }
    result = engine.classify_all(rebuild_reasons)
    assert result["s1"]["policy"] == "mandatory"
    assert result["s2"]["policy"] == "optional"
    assert result["s3"]["policy"] == "skip"


def test_mandatory_scene_ids():
    engine = RebuildPolicyEngine()
    policy_report = {
        "s1": {"policy": "mandatory"},
        "s2": {"policy": "optional"},
        "s3": {"policy": "skip"},
    }
    assert engine.mandatory_scene_ids(policy_report) == ["s1"]


def test_optional_scene_ids():
    engine = RebuildPolicyEngine()
    policy_report = {
        "s1": {"policy": "mandatory"},
        "s2": {"policy": "optional"},
    }
    assert engine.optional_scene_ids(policy_report) == ["s2"]


def test_skipped_scene_ids():
    engine = RebuildPolicyEngine()
    policy_report = {
        "s1": {"policy": "mandatory"},
        "s3": {"policy": "skip"},
    }
    assert engine.skipped_scene_ids(policy_report) == ["s3"]


def test_strength_at_mandatory_boundary():
    engine = RebuildPolicyEngine()
    report = engine.classify_scene([{"dependency_type": "avatar", "strength": 0.85}])
    assert report["policy"] == "mandatory"


def test_strength_just_below_mandatory_boundary():
    engine = RebuildPolicyEngine()
    report = engine.classify_scene([{"dependency_type": "avatar", "strength": 0.84}])
    assert report["policy"] == "optional"
