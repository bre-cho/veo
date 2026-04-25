"""Unit tests for the Scene Rerender module."""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# RerenderSceneRequest schema
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRerenderSceneRequest:
    def _req(self, **kwargs):
        from app.render.rerender.schemas import RerenderSceneRequest
        return RerenderSceneRequest(
            project_id="p1",
            episode_id="e1",
            scene_id="opening",
            **kwargs,
        )

    def test_default_mode_is_both(self):
        req = self._req()
        assert req.mode == "both"

    def test_force_defaults_false(self):
        req = self._req()
        assert req.force is False

    def test_mode_audio(self):
        req = self._req(mode="audio")
        assert req.mode == "audio"

    def test_mode_video(self):
        req = self._req(mode="video")
        assert req.mode == "video"

    def test_invalid_mode_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self._req(mode="invalid")

    def test_override_voiceover(self):
        req = self._req(override_voiceover_text="New text")
        assert req.override_voiceover_text == "New text"

    def test_override_duration(self):
        req = self._req(override_duration_sec=12.5)
        assert req.override_duration_sec == pytest.approx(12.5)


# ---------------------------------------------------------------------------
# RerenderService — full rerender (both)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRerenderServiceBothMode:
    def _setup(self, tmp_path):
        from app.render.manifest.manifest_service import ManifestService
        from app.render.rerender.rerender_service import RerenderService
        from app.render.rerender.schemas import RerenderSceneRequest

        class FakeTTS:
            def generate(self, payload):
                return {
                    "audio_url": "/audio/opening.wav",
                    "word_timings": [{"word": "It", "start_sec": 0.1, "end_sec": 0.3}],
                }

        class FakeVideo:
            def render_scene(self, payload):
                return {"video_path": "/video/opening.mp4"}

        svc = RerenderService(
            tts_service=FakeTTS(),
            video_service=FakeVideo(),
            manifest_base_dir=str(tmp_path),
        )

        # Seed a manifest with required fields
        manifest_svc = ManifestService(base_dir=str(tmp_path))
        manifest_svc.patch_scene("p1", "e1", "opening", {
            "status": "assembled",
            "voiceover_text": "It already happened.",
            "duration_sec": 8.0,
            "audio_path": "/old/audio.wav",
            "drama_metadata": {"emotion": "curiosity", "subtext": "trigger"},
        })

        req = RerenderSceneRequest(project_id="p1", episode_id="e1", scene_id="opening")
        return svc, manifest_svc, req

    def test_status_is_rerendered(self, tmp_path):
        svc, manifest_svc, req = self._setup(tmp_path)
        result = svc.rerender_scene(req)
        assert result["status"] == "rerendered"

    def test_needs_reassembly_true(self, tmp_path):
        svc, manifest_svc, req = self._setup(tmp_path)
        result = svc.rerender_scene(req)
        assert result["needs_reassembly"] is True

    def test_manifest_updated_with_new_audio(self, tmp_path):
        svc, manifest_svc, req = self._setup(tmp_path)
        svc.rerender_scene(req)
        data = manifest_svc.get_scene("p1", "e1", "opening")
        assert data["audio_path"] == "/audio/opening.wav"

    def test_manifest_updated_with_new_video(self, tmp_path):
        svc, manifest_svc, req = self._setup(tmp_path)
        svc.rerender_scene(req)
        data = manifest_svc.get_scene("p1", "e1", "opening")
        assert data["video_path"] == "/video/opening.mp4"

    def test_word_timings_saved_to_manifest(self, tmp_path):
        svc, manifest_svc, req = self._setup(tmp_path)
        svc.rerender_scene(req)
        data = manifest_svc.get_scene("p1", "e1", "opening")
        assert data["word_timings"] == [{"word": "It", "start_sec": 0.1, "end_sec": 0.3}]

    def test_audio_result_in_return_value(self, tmp_path):
        svc, manifest_svc, req = self._setup(tmp_path)
        result = svc.rerender_scene(req)
        assert result["audio_result"]["audio_url"] == "/audio/opening.wav"

    def test_video_result_in_return_value(self, tmp_path):
        svc, manifest_svc, req = self._setup(tmp_path)
        result = svc.rerender_scene(req)
        assert result["video_result"]["video_path"] == "/video/opening.mp4"


# ---------------------------------------------------------------------------
# RerenderService — audio-only mode
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRerenderServiceAudioMode:
    def _setup(self, tmp_path):
        from app.render.manifest.manifest_service import ManifestService
        from app.render.rerender.rerender_service import RerenderService
        from app.render.rerender.schemas import RerenderSceneRequest

        class FakeTTS:
            def generate(self, payload):
                return {"audio_url": "/audio/opening_v2.wav", "word_timings": []}

        class FakeVideo:
            def render_scene(self, payload):
                raise AssertionError("video_service should NOT be called in audio-only mode")

        svc = RerenderService(
            tts_service=FakeTTS(),
            video_service=FakeVideo(),
            manifest_base_dir=str(tmp_path),
        )

        manifest_svc = ManifestService(base_dir=str(tmp_path))
        manifest_svc.patch_scene("p1", "e1", "s1", {
            "voiceover_text": "Hello world",
            "duration_sec": 6.0,
        })

        req = RerenderSceneRequest(project_id="p1", episode_id="e1", scene_id="s1", mode="audio")
        return svc, manifest_svc, req

    def test_audio_only_does_not_call_video(self, tmp_path):
        svc, manifest_svc, req = self._setup(tmp_path)
        result = svc.rerender_scene(req)  # would raise if video called
        assert result["status"] == "rerendered"

    def test_audio_only_video_result_is_none(self, tmp_path):
        svc, manifest_svc, req = self._setup(tmp_path)
        result = svc.rerender_scene(req)
        assert result["video_result"] is None


# ---------------------------------------------------------------------------
# RerenderService — video-only mode
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRerenderServiceVideoMode:
    def _setup(self, tmp_path):
        from app.render.manifest.manifest_service import ManifestService
        from app.render.rerender.rerender_service import RerenderService
        from app.render.rerender.schemas import RerenderSceneRequest

        class FakeTTS:
            def generate(self, payload):
                raise AssertionError("tts_service should NOT be called in video-only mode")

        class FakeVideo:
            def render_scene(self, payload):
                return {"video_path": "/video/opening_v2.mp4"}

        svc = RerenderService(
            tts_service=FakeTTS(),
            video_service=FakeVideo(),
            manifest_base_dir=str(tmp_path),
        )

        manifest_svc = ManifestService(base_dir=str(tmp_path))
        manifest_svc.patch_scene("p1", "e1", "s1", {
            "voiceover_text": "Hello world",
            "duration_sec": 6.0,
            "audio_path": "/audio/existing.wav",
        })

        req = RerenderSceneRequest(project_id="p1", episode_id="e1", scene_id="s1", mode="video")
        return svc, manifest_svc, req

    def test_video_only_does_not_call_tts(self, tmp_path):
        svc, manifest_svc, req = self._setup(tmp_path)
        result = svc.rerender_scene(req)  # would raise if TTS called
        assert result["status"] == "rerendered"

    def test_video_only_audio_result_is_none(self, tmp_path):
        svc, manifest_svc, req = self._setup(tmp_path)
        result = svc.rerender_scene(req)
        assert result["audio_result"] is None

    def test_video_only_uses_existing_audio_path(self, tmp_path):
        svc, manifest_svc, req = self._setup(tmp_path)
        svc.rerender_scene(req)
        data = manifest_svc.get_scene("p1", "e1", "s1")
        assert data["video_path"] == "/video/opening_v2.mp4"


# ---------------------------------------------------------------------------
# RerenderService — error handling
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRerenderServiceErrors:
    def _make_service(self, tmp_path, tts_service=None, video_service=None):
        from app.render.rerender.rerender_service import RerenderService

        class _NoopTTS:
            def generate(self, p):
                return {"audio_url": "/a.wav", "word_timings": []}

        class _NoopVideo:
            def render_scene(self, p):
                return {"video_path": "/v.mp4"}

        return RerenderService(
            tts_service=tts_service or _NoopTTS(),
            video_service=video_service or _NoopVideo(),
            manifest_base_dir=str(tmp_path),
        )

    def test_raises_file_not_found_when_manifest_missing(self, tmp_path):
        from app.render.rerender.schemas import RerenderSceneRequest
        svc = self._make_service(tmp_path)
        req = RerenderSceneRequest(project_id="p", episode_id="e", scene_id="nope")
        with pytest.raises(FileNotFoundError):
            svc.rerender_scene(req)

    def test_raises_value_error_when_voiceover_missing(self, tmp_path):
        from app.render.manifest.manifest_service import ManifestService
        from app.render.rerender.schemas import RerenderSceneRequest
        ManifestService(base_dir=str(tmp_path)).patch_scene("p", "e", "s", {"duration_sec": 5})
        svc = self._make_service(tmp_path)
        req = RerenderSceneRequest(project_id="p", episode_id="e", scene_id="s")
        with pytest.raises(ValueError, match="voiceover_text"):
            svc.rerender_scene(req)

    def test_override_voiceover_used_when_manifest_missing_it(self, tmp_path):
        from app.render.manifest.manifest_service import ManifestService
        from app.render.rerender.schemas import RerenderSceneRequest
        ManifestService(base_dir=str(tmp_path)).patch_scene("p", "e", "s", {"duration_sec": 5})
        svc = self._make_service(tmp_path)
        req = RerenderSceneRequest(
            project_id="p", episode_id="e", scene_id="s",
            override_voiceover_text="Override text",
        )
        result = svc.rerender_scene(req)
        assert result["status"] == "rerendered"

    def test_manifest_status_set_to_rerender_failed_on_error(self, tmp_path):
        from app.render.manifest.manifest_service import ManifestService
        from app.render.rerender.schemas import RerenderSceneRequest

        class BrokenTTS:
            def generate(self, p):
                raise RuntimeError("TTS exploded")

        ManifestService(base_dir=str(tmp_path)).patch_scene("p", "e", "s", {
            "voiceover_text": "hello", "duration_sec": 5,
        })
        svc = self._make_service(tmp_path, tts_service=BrokenTTS())
        req = RerenderSceneRequest(project_id="p", episode_id="e", scene_id="s")
        with pytest.raises(RuntimeError):
            svc.rerender_scene(req)

        data = ManifestService(base_dir=str(tmp_path)).get_scene("p", "e", "s")
        assert data["status"] == "rerender_failed"
        assert data["error"]["type"] == "RuntimeError"
