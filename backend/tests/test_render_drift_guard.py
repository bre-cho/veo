"""Tests for the Timeline Drift Guard, Timeline Rebuilder, and Subtitle Rebuild Service."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_manifest(
    base_dir: str,
    project_id: str,
    episode_id: str,
    scene_id: str,
    data: Dict[str, Any],
) -> None:
    out = Path(base_dir) / project_id / episode_id
    out.mkdir(parents=True, exist_ok=True)
    payload = {"project_id": project_id, "episode_id": episode_id, "scene_id": scene_id, **data}
    (out / f"{scene_id}.json").write_text(json.dumps(payload))


def _read_manifest(
    base_dir: str,
    project_id: str,
    episode_id: str,
    scene_id: str,
) -> Dict[str, Any]:
    path = Path(base_dir) / project_id / episode_id / f"{scene_id}.json"
    return json.loads(path.read_text())


# ===========================================================================
# TimelineDriftGuard
# ===========================================================================

from app.render.reassembly.timeline_drift_guard import TimelineDriftGuard  # noqa: E402


class TestTimelineDriftGuard:
    def _guard(self):
        return TimelineDriftGuard()

    def test_no_drift_within_tolerance(self):
        report = self._guard().detect_drift(5.0, 5.1)
        assert report["has_drift"] is False

    def test_drift_detected_above_tolerance(self):
        report = self._guard().detect_drift(5.0, 8.2)
        assert report["has_drift"] is True

    def test_drift_sec_is_rounded(self):
        report = self._guard().detect_drift(5.0, 8.123456)
        assert report["drift_sec"] == pytest.approx(3.123, abs=1e-3)

    def test_negative_drift_detected(self):
        report = self._guard().detect_drift(8.0, 4.5)
        assert report["has_drift"] is True
        assert report["drift_sec"] < 0

    def test_zero_drift(self):
        report = self._guard().detect_drift(5.0, 5.0)
        assert report["has_drift"] is False
        assert report["drift_sec"] == 0.0

    def test_custom_tolerance(self):
        report = self._guard().detect_drift(5.0, 5.3, tolerance_sec=0.5)
        assert report["has_drift"] is False

    def test_report_contains_all_keys(self):
        report = self._guard().detect_drift(3.0, 6.5)
        assert {"has_drift", "drift_sec", "old_duration_sec", "new_duration_sec", "tolerance_sec"} == set(report)

    def test_compare_manifest_duration_no_drift(self):
        guard = self._guard()
        report = guard.compare_manifest_duration({"duration_sec": 5.0}, {"duration_sec": 5.05})
        assert report["has_drift"] is False

    def test_compare_manifest_duration_with_drift(self):
        guard = self._guard()
        report = guard.compare_manifest_duration({"duration_sec": 5.0}, {"duration_sec": 8.0})
        assert report["has_drift"] is True

    def test_compare_manifest_duration_missing_values(self):
        guard = self._guard()
        report = guard.compare_manifest_duration({}, {})
        assert report["old_duration_sec"] == 0.0
        assert report["new_duration_sec"] == 0.0


# ===========================================================================
# TimelineRebuilder
# ===========================================================================

from app.render.reassembly.timeline_rebuilder import (  # noqa: E402
    TimelineRebuilder,
    rebuild_global_word_timings,
)


class TestRebuildGlobalWordTimings:
    def test_applies_offset(self):
        item = {"word_timings": [{"word": "Hi", "start_sec": 0.5, "end_sec": 1.0}]}
        result = rebuild_global_word_timings(item, offset=10.0)
        assert result[0]["start_sec"] == pytest.approx(10.5)
        assert result[0]["end_sec"] == pytest.approx(11.0)

    def test_empty_word_timings(self):
        result = rebuild_global_word_timings({}, offset=5.0)
        assert result == []

    def test_multiple_words_with_offset(self):
        item = {
            "word_timings": [
                {"word": "Hello", "start_sec": 0.0, "end_sec": 0.5},
                {"word": "world", "start_sec": 0.6, "end_sec": 1.2},
            ]
        }
        result = rebuild_global_word_timings(item, offset=3.0)
        assert result[0]["start_sec"] == pytest.approx(3.0)
        assert result[1]["end_sec"] == pytest.approx(4.2)


class TestTimelineRebuilder:
    def test_rebuild_produces_correct_offsets(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        _write_manifest(manifests_dir, "p1", "ep1", "scene_001", {"duration_sec": 5.0, "word_timings": []})
        _write_manifest(manifests_dir, "p1", "ep1", "scene_002", {"duration_sec": 3.0, "word_timings": []})
        _write_manifest(manifests_dir, "p1", "ep1", "scene_003", {"duration_sec": 7.0, "word_timings": []})

        rebuilder = TimelineRebuilder()
        rebuilder.manifest = _make_manifest_service(manifests_dir)

        result = rebuilder.rebuild_episode_offsets("p1", "ep1")

        assert result["total_duration_sec"] == pytest.approx(15.0)
        offsets = {t["scene_id"]: t for t in result["timeline"]}
        assert offsets["scene_001"]["start_sec"] == pytest.approx(0.0)
        assert offsets["scene_002"]["start_sec"] == pytest.approx(5.0)
        assert offsets["scene_003"]["start_sec"] == pytest.approx(8.0)

    def test_rebuild_patches_manifests(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        _write_manifest(manifests_dir, "p1", "ep1", "scene_001", {"duration_sec": 4.0, "word_timings": []})
        _write_manifest(manifests_dir, "p1", "ep1", "scene_002", {"duration_sec": 6.0, "word_timings": []})

        rebuilder = TimelineRebuilder()
        rebuilder.manifest = _make_manifest_service(manifests_dir)
        rebuilder.rebuild_episode_offsets("p1", "ep1")

        s2 = _read_manifest(manifests_dir, "p1", "ep1", "scene_002")
        assert s2["timeline"]["start_sec"] == pytest.approx(4.0)
        assert s2["timeline"]["end_sec"] == pytest.approx(10.0)

    def test_rebuild_writes_global_word_timings(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        _write_manifest(manifests_dir, "p1", "ep1", "scene_001", {
            "duration_sec": 5.0,
            "word_timings": [{"word": "Hi", "start_sec": 0.1, "end_sec": 0.4}],
        })
        _write_manifest(manifests_dir, "p1", "ep1", "scene_002", {
            "duration_sec": 3.0,
            "word_timings": [{"word": "Bye", "start_sec": 0.2, "end_sec": 0.9}],
        })

        rebuilder = TimelineRebuilder()
        rebuilder.manifest = _make_manifest_service(manifests_dir)
        rebuilder.rebuild_episode_offsets("p1", "ep1")

        s2 = _read_manifest(manifests_dir, "p1", "ep1", "scene_002")
        assert s2["global_word_timings"][0]["start_sec"] == pytest.approx(5.2)

    def test_rebuild_sorts_by_scene_id(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        _write_manifest(manifests_dir, "p1", "ep1", "scene_003", {"duration_sec": 2.0, "word_timings": []})
        _write_manifest(manifests_dir, "p1", "ep1", "scene_001", {"duration_sec": 4.0, "word_timings": []})
        _write_manifest(manifests_dir, "p1", "ep1", "scene_002", {"duration_sec": 3.0, "word_timings": []})

        rebuilder = TimelineRebuilder()
        rebuilder.manifest = _make_manifest_service(manifests_dir)
        result = rebuilder.rebuild_episode_offsets("p1", "ep1")

        scene_ids = [t["scene_id"] for t in result["timeline"]]
        assert scene_ids == sorted(scene_ids)


# ===========================================================================
# SubtitleRebuildService
# ===========================================================================

from app.render.reassembly.subtitle_rebuild_service import SubtitleRebuildService  # noqa: E402


class TestSubtitleRebuildService:
    def test_rebuild_writes_ass_file(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        _write_manifest(manifests_dir, "p1", "ep1", "scene_001", {
            "global_word_timings": [{"word": "Hi", "start_sec": 0.0, "end_sec": 0.4}],
        })

        svc = SubtitleRebuildService()
        svc.manifest = _make_manifest_service(manifests_dir)

        with patch(
            "app.render.reassembly.subtitle_rebuild_service.write_visual_aware_karaoke_ass",
        ) as mock_write, patch("pathlib.Path.mkdir"):
            mock_write.return_value = "/data/renders/subtitles/p1/ep1.ass"
            result = svc.rebuild_episode_subtitles("p1", "ep1")

        assert result["status"] == "subtitle_rebuilt"
        assert result["scene_count"] == 1
        mock_write.assert_called_once()

    def test_rebuild_patches_subtitle_path_in_manifests(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        _write_manifest(manifests_dir, "p1", "ep1", "scene_001", {
            "global_word_timings": [{"word": "Hi", "start_sec": 0.0, "end_sec": 0.4}],
        })

        svc = SubtitleRebuildService()
        svc.manifest = _make_manifest_service(manifests_dir)

        subtitle_path = "/data/renders/subtitles/p1/ep1.ass"
        with patch(
            "app.render.reassembly.subtitle_rebuild_service.write_visual_aware_karaoke_ass",
            return_value=subtitle_path,
        ), patch("pathlib.Path.mkdir"):
            svc.rebuild_episode_subtitles("p1", "ep1")

        data = _read_manifest(manifests_dir, "p1", "ep1", "scene_001")
        assert data["subtitle_rebuilt_after_drift"] is True

    def test_build_global_words_fallback(self, tmp_path):
        svc = SubtitleRebuildService()
        manifest = {
            "timeline": {"start_sec": 10.0},
            "word_timings": [{"word": "Go", "start_sec": 0.1, "end_sec": 0.5}],
        }
        result = svc._build_global_words(manifest)
        assert result[0]["start_sec"] == pytest.approx(10.1)
        assert result[0]["end_sec"] == pytest.approx(10.5)

    def test_rebuild_uses_global_word_timings_first(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        _write_manifest(manifests_dir, "p1", "ep1", "scene_001", {
            "global_word_timings": [{"word": "Fast", "start_sec": 5.0, "end_sec": 5.5}],
            "word_timings": [{"word": "Slow", "start_sec": 0.0, "end_sec": 0.5}],
        })

        svc = SubtitleRebuildService()
        svc.manifest = _make_manifest_service(manifests_dir)

        captured_tracks = []

        def _capture(word_tracks, scene_placements, output_path):
            captured_tracks.extend(word_tracks)
            return output_path

        with patch(
            "app.render.reassembly.subtitle_rebuild_service.write_visual_aware_karaoke_ass",
            side_effect=_capture,
        ), patch("pathlib.Path.mkdir"):
            svc.rebuild_episode_subtitles("p1", "ep1")

        assert captured_tracks[0]["words"][0]["word"] == "Fast"


# ===========================================================================
# SmartReassemblyService — drift integration
# ===========================================================================

from app.render.reassembly.schemas import SmartReassemblyRequest  # noqa: E402
from app.render.reassembly.smart_reassembly_service import SmartReassemblyService  # noqa: E402


class TestSmartReassemblyDrift:
    def _req(self) -> SmartReassemblyRequest:
        return SmartReassemblyRequest(
            project_id="p1",
            episode_id="ep1",
            changed_scene_id="scene_002",
        )

    def _write_episode(self, manifests_dir: str) -> None:
        _write_manifest(manifests_dir, "p1", "ep1", "scene_001", {
            "scene_id": "scene_001",
            "video_path": "/v/s1.mp4",
            "audio_path": "/a/s1.wav",
            "duration_sec": 5.0,
            "word_timings": [],
        })
        _write_manifest(manifests_dir, "p1", "ep1", "scene_002", {
            "scene_id": "scene_002",
            "video_path": "/v/s2.mp4",
            "audio_path": "/a/s2.wav",
            "duration_sec": 8.0,         # new (longer)
            "previous_duration_sec": 5.0,  # was 5s, now 8s => +3s drift
            "word_timings": [],
        })

    def test_drift_detected_in_result(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        chunks_dir = str(tmp_path / "chunks")
        self._write_episode(manifests_dir)

        svc = SmartReassemblyService(
            manifest_base_dir=manifests_dir,
            chunk_base_dir=chunks_dir,
        )

        mock_chunk = {"scene_id": "scene_002", "chunk_path": "/c/s2.mp4", "duration_sec": 8.0}
        mock_final = {"status": "succeeded", "output_path": "/final/ep1.mp4"}
        mock_timeline = {"total_duration_sec": 13.0, "timeline": []}
        mock_subtitle = {"status": "subtitle_rebuilt", "subtitle_path": "/subs/ep1.ass", "scene_count": 2, "word_track_count": 0}

        with patch.object(svc._chunk_builder, "build_scene_chunk", return_value=mock_chunk), \
             patch.object(svc._finalizer, "concat_chunks", return_value=mock_final), \
             patch.object(svc._timeline_rebuilder, "rebuild_episode_offsets", return_value=mock_timeline), \
             patch.object(svc._subtitle_rebuilder, "rebuild_episode_subtitles", return_value=mock_subtitle):
            result = svc.reassemble(self._req())

        assert result["timeline_drift"]["has_drift"] is True
        assert result["timeline_drift"]["drift_sec"] == pytest.approx(3.0)
        assert result["timeline_report"] == mock_timeline
        assert result["subtitle_report"] == mock_subtitle

    def test_no_drift_skips_rebuild(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        chunks_dir = str(tmp_path / "chunks")
        _write_manifest(manifests_dir, "p1", "ep1", "scene_002", {
            "scene_id": "scene_002",
            "video_path": "/v/s2.mp4",
            "audio_path": "/a/s2.wav",
            "duration_sec": 5.0,
            "previous_duration_sec": 5.0,  # no change
            "word_timings": [],
        })

        svc = SmartReassemblyService(
            manifest_base_dir=manifests_dir,
            chunk_base_dir=chunks_dir,
        )

        mock_chunk = {"scene_id": "scene_002", "chunk_path": "/c/s2.mp4", "duration_sec": 5.0}
        mock_final = {"status": "succeeded", "output_path": "/final/ep1.mp4"}

        with patch.object(svc._chunk_builder, "build_scene_chunk", return_value=mock_chunk), \
             patch.object(svc._finalizer, "concat_chunks", return_value=mock_final), \
             patch.object(svc._timeline_rebuilder, "rebuild_episode_offsets") as mock_tl, \
             patch.object(svc._subtitle_rebuilder, "rebuild_episode_subtitles") as mock_sub:
            result = svc.reassemble(self._req())

        mock_tl.assert_not_called()
        mock_sub.assert_not_called()
        assert result["timeline_drift"]["has_drift"] is False
        assert result["timeline_report"] is None
        assert result["subtitle_report"] is None


# ===========================================================================
# ChunkIndex — total_duration_sec
# ===========================================================================

from app.render.reassembly.chunk_index import ChunkIndex  # noqa: E402


class TestChunkIndexTotalDuration:
    def test_total_duration_updated_after_update_chunk(self, tmp_path):
        ci = ChunkIndex(base_dir=str(tmp_path / "chunks"))
        ci.update_chunk("p1", "ep1", "s1", "/c/s1.mp4", 5.0)
        ci.update_chunk("p1", "ep1", "s2", "/c/s2.mp4", 3.5)
        index = ci.load("p1", "ep1")
        assert index["total_duration_sec"] == pytest.approx(8.5)

    def test_total_duration_updates_on_replace(self, tmp_path):
        ci = ChunkIndex(base_dir=str(tmp_path / "chunks"))
        ci.update_chunk("p1", "ep1", "s1", "/c/s1.mp4", 5.0)
        ci.update_chunk("p1", "ep1", "s1", "/c/s1_new.mp4", 8.0)
        index = ci.load("p1", "ep1")
        assert index["total_duration_sec"] == pytest.approx(8.0)


# ===========================================================================
# RerenderService — previous_duration_sec persisted
# ===========================================================================


class TestRerenderPreviousDuration:
    def _setup(self, tmp_path, new_duration: float = 11.0):
        from app.render.manifest.manifest_service import ManifestService
        from app.render.rerender.rerender_service import RerenderService
        from app.render.rerender.schemas import RerenderSceneRequest

        class FakeTTS:
            def __init__(self, dur):
                self._dur = dur

            def generate(self, payload):
                return {
                    "audio_url": "/audio/s.wav",
                    "word_timings": [],
                    "duration_sec": self._dur,
                }

        class FakeVideo:
            def render_scene(self, payload):
                return {"video_path": "/video/s.mp4"}

        svc = RerenderService(
            tts_service=FakeTTS(new_duration),
            video_service=FakeVideo(),
            manifest_base_dir=str(tmp_path),
        )

        manifest_svc = ManifestService(base_dir=str(tmp_path))
        manifest_svc.patch_scene("p1", "e1", "s1", {
            "voiceover_text": "Hello",
            "duration_sec": 8.0,
        })

        req = RerenderSceneRequest(project_id="p1", episode_id="e1", scene_id="s1")
        return svc, manifest_svc, req

    def test_previous_duration_sec_saved(self, tmp_path):
        svc, manifest_svc, req = self._setup(tmp_path)
        svc.rerender_scene(req)
        data = manifest_svc.get_scene("p1", "e1", "s1")
        assert data["previous_duration_sec"] == pytest.approx(8.0)

    def test_new_duration_sec_saved_from_tts(self, tmp_path):
        svc, manifest_svc, req = self._setup(tmp_path, new_duration=11.0)
        svc.rerender_scene(req)
        data = manifest_svc.get_scene("p1", "e1", "s1")
        assert data["duration_sec"] == pytest.approx(11.0)

    def test_original_duration_used_when_tts_returns_none(self, tmp_path):
        from app.render.manifest.manifest_service import ManifestService
        from app.render.rerender.rerender_service import RerenderService
        from app.render.rerender.schemas import RerenderSceneRequest

        class FakeTTSNoDuration:
            def generate(self, payload):
                return {"audio_url": "/audio/s.wav", "word_timings": []}

        svc = RerenderService(
            tts_service=FakeTTSNoDuration(),
            video_service=MagicMock(render_scene=lambda p: {"video_path": "/v.mp4"}),
            manifest_base_dir=str(tmp_path),
        )

        ManifestService(base_dir=str(tmp_path)).patch_scene("p1", "e1", "s1", {
            "voiceover_text": "Hello",
            "duration_sec": 8.0,
        })

        req = RerenderSceneRequest(project_id="p1", episode_id="e1", scene_id="s1")
        svc.rerender_scene(req)
        data = ManifestService(base_dir=str(tmp_path)).get_scene("p1", "e1", "s1")
        # Falls back to original duration_sec
        assert data["duration_sec"] == pytest.approx(8.0)


# ---------------------------------------------------------------------------
# Helpers — inline ManifestService pointing at tmp dir
# ---------------------------------------------------------------------------


def _make_manifest_service(base_dir: str):
    from app.render.manifest.manifest_service import ManifestService
    return ManifestService(base_dir=base_dir)
