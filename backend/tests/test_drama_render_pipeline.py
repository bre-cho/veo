"""Unit tests for the Render Pipeline Integration patch."""
from __future__ import annotations

import pytest


@pytest.mark.unit
class TestScriptToRenderAdapter:
    def _make_adapter(self):
        from app.drama.render.adapters.script_to_render_adapter import ScriptToRenderAdapter
        return ScriptToRenderAdapter()

    def test_adapt_empty_segments(self):
        adapter = self._make_adapter()
        result = adapter.adapt({"segments": []})
        assert result == []

    def test_adapt_single_segment(self):
        adapter = self._make_adapter()
        script_output = {
            "segments": [
                {
                    "scene_id": "opening",
                    "purpose": "hook",
                    "text": "It already happened.",
                    "duration_sec": 8,
                    "subtext": "trigger",
                    "intent": "capture_attention",
                    "emotion": "curiosity",
                    "voice": {
                        "tone": "low, suspenseful",
                        "speed": "slow",
                        "pause": "long",
                        "stress_words": ["happened"],
                    },
                }
            ]
        }
        scenes = adapter.adapt(script_output)
        assert len(scenes) == 1
        scene = scenes[0]
        assert scene["scene_index"] == 0
        assert scene["scene_id"] == "opening"
        assert scene["render_purpose"] == "hook"
        assert scene["voiceover_text"] == "It already happened."
        assert scene["duration_sec"] == 8
        assert scene["voice_directive"]["tone"] == "low, suspenseful"
        assert scene["voice_directive"]["speed"] == "slow"
        assert scene["voice_directive"]["pause"] == "long"
        assert scene["voice_directive"]["stress_words"] == ["happened"]
        assert scene["drama_metadata"]["subtext"] == "trigger"
        assert scene["drama_metadata"]["intent"] == "capture_attention"
        assert scene["drama_metadata"]["emotion"] == "curiosity"

    def test_adapt_defaults_for_missing_voice(self):
        adapter = self._make_adapter()
        script_output = {
            "segments": [
                {"scene_id": "s1", "purpose": "context", "text": "Hello.", "duration_sec": 6},
            ]
        }
        scenes = adapter.adapt(script_output)
        vd = scenes[0]["voice_directive"]
        assert vd["tone"] == "documentary, calm"
        assert vd["speed"] == "normal"
        assert vd["pause"] == "normal"
        assert vd["stress_words"] == []

    def test_adapt_scene_index_increments(self):
        adapter = self._make_adapter()
        script_output = {
            "segments": [
                {"scene_id": "a", "text": "A"},
                {"scene_id": "b", "text": "B"},
                {"scene_id": "c", "text": "C"},
            ]
        }
        scenes = adapter.adapt(script_output)
        assert [s["scene_index"] for s in scenes] == [0, 1, 2]


@pytest.mark.unit
class TestRenderJobService:
    def _create_jobs(self, script_output):
        from app.drama.render.services.render_job_service import create_render_job_from_script
        return create_render_job_from_script("proj_001", script_output)

    def _make_render_scenes(self):
        return [
            {
                "scene_id": "opening",
                "render_purpose": "hook",
                "voiceover_text": "It already happened.",
                "duration_sec": 8,
                "voice_directive": {"tone": "low", "speed": "slow", "pause": "long", "stress_words": []},
                "drama_metadata": {"subtext": "trigger", "intent": "capture", "emotion": "curiosity"},
            }
        ]

    def test_creates_one_job_per_scene(self):
        jobs = self._create_jobs({"render_scenes": self._make_render_scenes()})
        assert len(jobs) == 1

    def test_job_has_required_fields(self):
        jobs = self._create_jobs({"render_scenes": self._make_render_scenes()})
        job = jobs[0]
        assert job["project_id"] == "proj_001"
        assert job["scene_id"] == "opening"
        assert job["status"] == "queued"
        assert job["voiceover_text"] == "It already happened."
        assert job["duration_sec"] == 8
        assert job["voice_tone"] == "low"
        assert job["voice_speed"] == "slow"
        assert job["voice_pause"] == "long"
        assert job["render_purpose"] == "hook"
        assert job["subtext"] == "trigger"
        assert job["intent"] == "capture"
        assert job["emotion"] == "curiosity"

    def test_empty_render_scenes(self):
        jobs = self._create_jobs({"render_scenes": []})
        assert jobs == []

    def test_missing_render_scenes_key(self):
        jobs = self._create_jobs({})
        assert jobs == []


@pytest.mark.unit
class TestNextLevelScriptService:
    def _make_service(self):
        from app.drama.script.services.next_level_script_service import NextLevelScriptService
        return NextLevelScriptService()

    def _make_payload(self):
        from app.drama.script.schemas.next_level_script_request import NextLevelScriptRequest
        return NextLevelScriptRequest(
            project_id="proj_001",
            episode_id="ep_001",
            topic="quantum computing",
        )

    def test_generate_returns_render_scenes(self):
        svc = self._make_service()
        output = svc.generate(self._make_payload())
        assert "render_scenes" in output
        assert isinstance(output["render_scenes"], list)
        assert len(output["render_scenes"]) > 0

    def test_generate_returns_full_script(self):
        svc = self._make_service()
        output = svc.generate(self._make_payload())
        assert "full_script" in output
        assert isinstance(output["full_script"], str)
        assert len(output["full_script"]) > 0

    def test_render_scenes_have_required_keys(self):
        svc = self._make_service()
        output = svc.generate(self._make_payload())
        for scene in output["render_scenes"]:
            assert "scene_id" in scene
            assert "voiceover_text" in scene
            assert "duration_sec" in scene
            assert "voice_directive" in scene
            assert "drama_metadata" in scene
