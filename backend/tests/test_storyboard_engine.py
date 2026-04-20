from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.storyboard_engine import SceneBeat, StoryboardEngine

client = TestClient(app)
_engine = StoryboardEngine()


# ---------------------------------------------------------------------------
# StoryboardEngine unit tests
# ---------------------------------------------------------------------------

def test_parse_returns_list_of_scene_beats() -> None:
    script = "Struggling with deadlines?\n\nProjects always run over budget.\n\nIntroducing TaskMaster.\n\nGet it now — link in bio."
    beats = _engine.parse_script(script)
    assert len(beats) >= 1
    for b in beats:
        assert isinstance(b, SceneBeat)


def test_first_beat_is_always_hook() -> None:
    script = "What if you never missed a deadline again?\n\nMost teams struggle with chaos.\n\nMeet TaskMaster."
    beats = _engine.parse_script(script)
    assert beats[0].scene_goal == "hook"


def test_last_beat_with_cta_signal_is_cta() -> None:
    script = "Did you know?\n\nMost people fail at budgets.\n\nHere's the fix.\n\nGet started today — click the link."
    beats = _engine.parse_script(script)
    assert beats[-1].cta_flag is True


def test_beat_has_required_fields() -> None:
    beats = _engine.parse_script("Struggling?\n\nThis product is the answer.\n\nBuy now.")
    for b in beats:
        assert b.scene_goal in ("hook", "build_tension", "reveal", "body", "cta")
        assert b.visual_type != ""
        assert b.emotion != ""
        assert isinstance(b.cta_flag, bool)
        assert b.script_text.strip() != ""


def test_empty_script_returns_empty_list() -> None:
    assert _engine.parse_script("") == []
    assert _engine.parse_script([]) == []
    assert _engine.parse_script("   ") == []


def test_max_scenes_respected() -> None:
    long_script = "\n\n".join([f"Line {i}" for i in range(20)])
    beats = _engine.parse_script(long_script, max_scenes=5)
    assert len(beats) <= 5


def test_list_input_accepted() -> None:
    lines = ["Struggling with pain?", "The problem is real.", "Get help now."]
    beats = _engine.parse_script(lines)
    assert len(beats) == 3


def test_to_scene_dicts_returns_dicts() -> None:
    dicts = _engine.to_scene_dicts("Hook line.\n\nBody line.\n\nCTA line - click now.")
    assert isinstance(dicts, list)
    assert all(isinstance(d, dict) for d in dicts)
    assert all("scene_goal" in d for d in dicts)


def test_tension_classified_correctly() -> None:
    script = "Hook!\n\nThis is a serious problem that wastes time.\n\nGet help now."
    beats = _engine.parse_script(script)
    goals = [b.scene_goal for b in beats]
    assert "build_tension" in goals


def test_reveal_classified_correctly() -> None:
    script = "Hook!\n\nThe problem is real.\n\nIntroducing the solution you've been waiting for."
    beats = _engine.parse_script(script)
    goals = [b.scene_goal for b in beats]
    assert "reveal" in goals


def test_beat_to_dict_structure() -> None:
    beats = _engine.parse_script("Hook\n\nBody\n\nCTA click now")
    for d in (b.to_dict() for b in beats):
        assert "scene_index" in d
        assert "scene_goal" in d
        assert "visual_type" in d
        assert "emotion" in d
        assert "cta_flag" in d
        assert "script_text" in d
        assert "title" in d
        assert "metadata" in d


# ---------------------------------------------------------------------------
# Storyboard API endpoint tests
# ---------------------------------------------------------------------------

def test_storyboard_generate_api_happy_path() -> None:
    resp = client.post(
        "/api/v1/storyboard/generate",
        json={"script": "Did you know?\n\nMost fail at this.\n\nIntroducing TaskMaster.\n\nGet it now."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["scene_count"] > 0
    assert len(data["scenes"]) == data["scene_count"]
    scene = data["scenes"][0]
    assert scene["scene_goal"] == "hook"
    assert scene["visual_type"] != ""
    assert scene["emotion"] != ""


def test_storyboard_generate_api_max_scenes() -> None:
    long = "\n\n".join([f"Paragraph {i}" for i in range(15)])
    resp = client.post(
        "/api/v1/storyboard/generate",
        json={"script": long, "max_scenes": 4},
    )
    assert resp.status_code == 200
    assert resp.json()["scene_count"] <= 4


def test_storyboard_generate_api_empty_script_rejected() -> None:
    resp = client.post("/api/v1/storyboard/generate", json={"script": ""})
    assert resp.status_code == 422
