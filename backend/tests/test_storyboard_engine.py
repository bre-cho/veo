from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.storyboard_engine import StoryboardEngine


client = TestClient(app)
_engine = StoryboardEngine()


def test_generate_storyboard_from_script_text() -> None:
    result = _engine.generate_from_script(
        script_text="Did you know your hooks lose viewers?\n\nMost creators struggle with weak intros.\n\nTap now to fix it.",
        content_goal="conversion",
    )
    assert result.scenes
    assert result.scenes[0].scene_goal == "hook"


def test_generate_storyboard_from_preview_payload() -> None:
    payload = {
        "script_text": "Hook line\n\nBody line\n\nBuy now",
        "scenes": [
            {"scene_index": 1, "script_text": "Hook line"},
            {"scene_index": 2, "script_text": "Body line"},
            {"scene_index": 3, "script_text": "Buy now"},
        ],
    }
    result = _engine.generate_from_preview(payload)
    assert len(result.scenes) >= 3
    assert result.summary["scene_count"] >= 3


def test_scene_has_goal_cta_and_shot_hint() -> None:
    result = _engine.generate_from_script(script_text="Question?\n\nExplain value\n\nClick now")
    first = result.scenes[0]
    assert first.scene_goal
    assert isinstance(first.cta_flag, bool)
    assert first.shot_hint


def test_conversion_mode_increases_cta_placement() -> None:
    with_conversion = _engine.generate_from_script(
        script_text="Hook\n\nBody",
        conversion_mode="direct",
        content_goal="conversion",
    )
    without_conversion = _engine.generate_from_script(script_text="Hook\n\nBody")
    assert sum(1 for s in with_conversion.scenes if s.cta_flag) >= sum(1 for s in without_conversion.scenes if s.cta_flag)


def test_storyboard_generate_api() -> None:
    resp = client.post(
        "/api/v1/storyboard/generate",
        json={"script_text": "Did you know?\n\nTry this now", "conversion_mode": "direct"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["storyboard_id"]
    assert data["scenes"]
