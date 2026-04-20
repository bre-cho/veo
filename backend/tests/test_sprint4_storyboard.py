"""Sprint 4 – Storyboard + Director Engine tests.

Covers:
- beat_map_generator: beat map structure and on-beat alignment
- scene_dependency_graph: nodes, edges, connectivity
- Platform grammar injection: hook_weight, cta_position, transition_style
- hook → build-up → CTA optimisation: CTA always last in short-form
- hook_retention_score: computed and in range [0, 1]
- Backward compatibility: existing generate_from_script still works without platform
"""
from __future__ import annotations

import pytest

from app.services.storyboard_engine import (
    StoryboardEngine,
    _build_beat_map,
    _build_scene_dependency_graph,
    _get_platform_grammar,
)


_eng = StoryboardEngine()

_SAMPLE_SCRIPT = """
Are you still struggling with slow software?

The problem is most tools aren't built for speed or simplicity.

Introducing TaskFlow — the fastest setup in the industry.

Thousands of teams have switched and saved hours every week.

Start your free trial now and see the results.
""".strip()


# ---------------------------------------------------------------------------
# Platform grammar resolution
# ---------------------------------------------------------------------------

def test_tiktok_grammar_hook_weight() -> None:
    grammar = _get_platform_grammar("tiktok")
    assert grammar["hook_weight"] > 1.0
    assert grammar["max_hook_sec"] <= 5.0


def test_youtube_grammar_longer_ideal_duration() -> None:
    grammar = _get_platform_grammar("youtube")
    tiktok = _get_platform_grammar("tiktok")
    assert grammar["ideal_scene_duration"] > tiktok["ideal_scene_duration"]


def test_unknown_platform_falls_back_to_default() -> None:
    grammar = _get_platform_grammar("unknown_platform_xyz")
    default = _get_platform_grammar(None)
    assert grammar == default


# ---------------------------------------------------------------------------
# beat_map_generator
# ---------------------------------------------------------------------------

def test_beat_map_includes_all_expected_keys() -> None:
    resp = _eng.generate_from_script(script_text=_SAMPLE_SCRIPT, platform="tiktok")
    beat_map = resp.summary.get("beat_map", [])
    assert len(beat_map) > 0
    for beat in beat_map:
        assert "beat_index" in beat
        assert "expected_beat" in beat
        assert "on_beat" in beat
        assert "pacing_weight" in beat


def test_beat_map_first_beat_is_hook() -> None:
    resp = _eng.generate_from_script(script_text=_SAMPLE_SCRIPT, platform="tiktok")
    beat_map = resp.summary["beat_map"]
    assert beat_map[0]["expected_beat"] == "hook"


# ---------------------------------------------------------------------------
# scene_dependency_graph
# ---------------------------------------------------------------------------

def test_dependency_graph_structure() -> None:
    resp = _eng.generate_from_script(script_text=_SAMPLE_SCRIPT, platform="youtube")
    graph = resp.summary.get("dependency_graph", {})
    assert "nodes" in graph
    assert "edges" in graph
    assert len(graph["nodes"]) == len(resp.scenes)
    # Edges should be scene_count - 1 for a linear story
    assert len(graph["edges"]) == len(resp.scenes) - 1


def test_dependency_graph_nodes_have_scene_goal() -> None:
    resp = _eng.generate_from_script(script_text=_SAMPLE_SCRIPT)
    graph = resp.summary["dependency_graph"]
    for node in graph["nodes"]:
        assert "scene_goal" in node
        assert node["scene_goal"] is not None


def test_dependency_graph_edges_sequential() -> None:
    resp = _eng.generate_from_script(script_text=_SAMPLE_SCRIPT)
    graph = resp.summary["dependency_graph"]
    for edge in graph["edges"]:
        assert edge["type"] == "sequential"
        assert "transition" in edge


# ---------------------------------------------------------------------------
# Hook → build-up → CTA optimisation
# ---------------------------------------------------------------------------

def test_hook_is_first_scene() -> None:
    resp = _eng.generate_from_script(script_text=_SAMPLE_SCRIPT, platform="tiktok")
    assert resp.scenes[0].scene_goal == "hook"


def test_cta_is_last_scene_for_short_form() -> None:
    resp = _eng.generate_from_script(
        script_text=_SAMPLE_SCRIPT,
        platform="tiktok",
        conversion_mode="direct",
    )
    # CTA should end up at the end after flow optimisation
    last_goal = resp.scenes[-1].scene_goal
    assert last_goal == "cta"


def test_hook_retention_score_present_and_valid() -> None:
    resp = _eng.generate_from_script(script_text=_SAMPLE_SCRIPT, platform="tiktok")
    score = resp.summary.get("hook_retention_score")
    assert score is not None
    assert 0.0 <= score <= 1.0


def test_hook_retention_score_higher_with_open_loop() -> None:
    script_with_question = "Are you tired of slow results?\n\nHere's what you need.\n\nTry it now."
    resp = _eng.generate_from_script(script_text=script_with_question, platform="tiktok")
    assert resp.summary["hook_retention_score"] > 0.3


# ---------------------------------------------------------------------------
# Platform grammar injected into pacing weights
# ---------------------------------------------------------------------------

def test_tiktok_hook_pacing_weight_higher_than_youtube() -> None:
    resp_tiktok = _eng.generate_from_script(script_text=_SAMPLE_SCRIPT, platform="tiktok")
    resp_youtube = _eng.generate_from_script(script_text=_SAMPLE_SCRIPT, platform="youtube")

    tiktok_hook = next(s for s in resp_tiktok.scenes if s.scene_goal == "hook")
    youtube_hook = next(s for s in resp_youtube.scenes if s.scene_goal == "hook")
    assert tiktok_hook.pacing_weight >= youtube_hook.pacing_weight


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------

def test_generate_from_script_without_platform_still_works() -> None:
    resp = _eng.generate_from_script(script_text=_SAMPLE_SCRIPT)
    assert len(resp.scenes) > 0
    assert resp.summary["scene_count"] == len(resp.scenes)


def test_parse_script_backward_compat() -> None:
    scenes = _eng.parse_script(_SAMPLE_SCRIPT, max_scenes=3)
    assert len(scenes) <= 3
    assert scenes[0].scene_goal == "hook"
