"""Unit tests for the Scene Timeline Compiler patch."""
from __future__ import annotations

import pytest


def _make_render_scenes(count: int = 3):
    scenes = [
        {
            "scene_id": "opening",
            "render_purpose": "hook",
            "voiceover_text": "It already happened you just didn't notice.",
            "duration_sec": 8,
            "voice_directive": {"tone": "low", "speed": "slow", "pause": "long", "stress_words": []},
            "drama_metadata": {"subtext": "trigger", "intent": "capture_attention", "emotion": "curiosity"},
        },
        {
            "scene_id": "context",
            "render_purpose": "context",
            "voiceover_text": "Here is what is really going on.",
            "duration_sec": 6,
            "voice_directive": {"tone": "calm", "speed": "normal", "pause": "normal", "stress_words": []},
            "drama_metadata": {"subtext": "frame", "intent": "set_context", "emotion": "intrigue"},
        },
        {
            "scene_id": "reveal",
            "render_purpose": "reveal",
            "voiceover_text": "And this changes everything.",
            "duration_sec": 5,
            "voice_directive": {"tone": "dramatic", "speed": "normal", "pause": "short", "stress_words": ["changes"]},
            "drama_metadata": {"subtext": "pivot", "intent": "deliver_reveal", "emotion": "awe"},
        },
    ]
    return scenes[:count]


@pytest.mark.unit
class TestAudioTimingEngine:
    def test_continuous_timing(self):
        from app.drama.timeline.engines.audio_timing_engine import compile_audio_timing
        scenes = _make_render_scenes(3)
        tracks = compile_audio_timing(scenes)
        assert len(tracks) == 3
        assert tracks[0]["start_sec"] == 0
        assert tracks[0]["end_sec"] == 8
        assert tracks[1]["start_sec"] == 8
        assert tracks[1]["end_sec"] == 14
        assert tracks[2]["start_sec"] == 14
        assert tracks[2]["end_sec"] == 19

    def test_duration_matches_scene(self):
        from app.drama.timeline.engines.audio_timing_engine import compile_audio_timing
        scenes = _make_render_scenes(1)
        tracks = compile_audio_timing(scenes)
        assert tracks[0]["duration_sec"] == 8

    def test_empty_scenes(self):
        from app.drama.timeline.engines.audio_timing_engine import compile_audio_timing
        assert compile_audio_timing([]) == []


@pytest.mark.unit
class TestSubtitleTimingEngine:
    def test_subtitle_chunks_within_scene_duration(self):
        from app.drama.timeline.engines.subtitle_timing_engine import compile_subtitle_timing
        scenes = _make_render_scenes(1)
        subtitles = compile_subtitle_timing(scenes)
        assert len(subtitles) >= 1
        for sub in subtitles:
            assert sub["start_sec"] >= 0
            assert sub["end_sec"] <= scenes[0]["duration_sec"] + 0.01  # float tolerance

    def test_empty_text_fallback(self):
        from app.drama.timeline.engines.subtitle_timing_engine import compile_subtitle_timing, split_subtitle_text
        assert split_subtitle_text("") == [""]

    def test_split_subtitle_text_chunks(self):
        from app.drama.timeline.engines.subtitle_timing_engine import split_subtitle_text
        text = " ".join([str(i) for i in range(15)])
        chunks = split_subtitle_text(text)
        assert len(chunks) == 3
        assert all(len(c.split()) <= 7 for c in chunks)


@pytest.mark.unit
class TestTransitionEngine:
    def test_transition_count_equals_scenes_minus_one(self):
        from app.drama.timeline.engines.transition_engine import compile_transitions
        scenes = _make_render_scenes(3)
        transitions = compile_transitions(scenes)
        assert len(transitions) == 2

    def test_single_scene_no_transitions(self):
        from app.drama.timeline.engines.transition_engine import compile_transitions
        assert compile_transitions(_make_render_scenes(1)) == []

    def test_reveal_produces_hard_cut(self):
        from app.drama.timeline.engines.transition_engine import compile_transitions
        scenes = _make_render_scenes(3)
        transitions = compile_transitions(scenes)
        # context -> reveal should be hard_cut
        reveal_transition = next(t for t in transitions if t["to_scene_id"] == "reveal")
        assert reveal_transition["transition_type"] == "hard_cut"

    def test_hook_start_produces_match_cut(self):
        from app.drama.timeline.engines.transition_engine import compile_transitions
        scenes = _make_render_scenes(2)
        transitions = compile_transitions(scenes)
        assert transitions[0]["transition_type"] == "match_cut"


@pytest.mark.unit
class TestSceneTimelineCompiler:
    def _make_compiler(self):
        from app.drama.timeline.engines.timeline_compiler import SceneTimelineCompiler
        return SceneTimelineCompiler()

    def test_compile_total_duration(self):
        compiler = self._make_compiler()
        scenes = _make_render_scenes(3)
        result = compiler.compile("proj_001", "ep_001", scenes)
        assert result["total_duration_sec"] == 8 + 6 + 5

    def test_compile_scene_timing_continuous(self):
        compiler = self._make_compiler()
        result = compiler.compile("proj_001", "ep_001", _make_render_scenes(3))
        compiled_scenes = result["scenes"]
        assert compiled_scenes[0]["start_sec"] == 0
        assert compiled_scenes[1]["start_sec"] == 8
        assert compiled_scenes[2]["start_sec"] == 14

    def test_compile_returns_all_keys(self):
        compiler = self._make_compiler()
        result = compiler.compile("proj_001", "ep_001", _make_render_scenes(2))
        for key in ("project_id", "episode_id", "total_duration_sec", "scenes",
                    "subtitle_tracks", "audio_tracks", "transition_map", "assembly_plan"):
            assert key in result

    def test_assembly_plan_has_output_config(self):
        compiler = self._make_compiler()
        result = compiler.compile("proj_001", "ep_001", _make_render_scenes(1))
        plan = result["assembly_plan"]
        assert plan["output"]["format"] == "mp4"
        assert plan["output"]["fps"] == 24

    def test_empty_scenes(self):
        compiler = self._make_compiler()
        result = compiler.compile("proj_001", "ep_001", [])
        assert result["total_duration_sec"] == 0
        assert result["scenes"] == []
        assert result["transition_map"] == []


@pytest.mark.unit
class TestTimelineService:
    def _make_service(self):
        from app.drama.timeline.services.timeline_service import TimelineService
        return TimelineService()

    def test_service_delegates_to_compiler(self):
        from app.drama.timeline.schemas.timeline_request import TimelineRequest
        svc = self._make_service()
        payload = TimelineRequest(
            project_id="proj_001",
            episode_id="ep_001",
            render_scenes=_make_render_scenes(2),
        )
        result = svc.compile(payload)
        assert result["project_id"] == "proj_001"
        assert result["episode_id"] == "ep_001"
        assert len(result["scenes"]) == 2
