"""Tests for AffectedRangeResolver, BurnInModeResolver,
PerSceneSubtitleService, and the updated SmartReassemblyService."""
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
    payload = {
        "project_id": project_id,
        "episode_id": episode_id,
        "scene_id": scene_id,
        **data,
    }
    (out / f"{scene_id}.json").write_text(json.dumps(payload))


def _read_manifest(
    base_dir: str,
    project_id: str,
    episode_id: str,
    scene_id: str,
) -> Dict[str, Any]:
    path = Path(base_dir) / project_id / episode_id / f"{scene_id}.json"
    return json.loads(path.read_text())


def _make_manifest_service(base_dir: str):
    from app.render.manifest.manifest_service import ManifestService
    return ManifestService(base_dir=base_dir)


# ===========================================================================
# AffectedRangeResolver
# ===========================================================================

from app.render.reassembly.affected_range_resolver import AffectedRangeResolver  # noqa: E402


class TestAffectedRangeResolver:
    def _write_episode(self, manifests_dir: str) -> None:
        for sid in ("scene_001", "scene_002", "scene_003", "scene_004", "scene_005"):
            _write_manifest(manifests_dir, "p1", "ep1", sid, {"duration_sec": 5.0})

    def test_no_drift_returns_only_changed_scene(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        self._write_episode(manifests_dir)

        resolver = AffectedRangeResolver()
        resolver.manifest = _make_manifest_service(manifests_dir)

        result = resolver.resolve("p1", "ep1", "scene_003", has_timeline_drift=False)
        assert [r["scene_id"] for r in result] == ["scene_003"]

    def test_drift_returns_changed_scene_and_all_following(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        self._write_episode(manifests_dir)

        resolver = AffectedRangeResolver()
        resolver.manifest = _make_manifest_service(manifests_dir)

        result = resolver.resolve("p1", "ep1", "scene_003", has_timeline_drift=True)
        assert [r["scene_id"] for r in result] == ["scene_003", "scene_004", "scene_005"]

    def test_drift_on_first_scene_returns_all(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        self._write_episode(manifests_dir)

        resolver = AffectedRangeResolver()
        resolver.manifest = _make_manifest_service(manifests_dir)

        result = resolver.resolve("p1", "ep1", "scene_001", has_timeline_drift=True)
        assert len(result) == 5

    def test_drift_on_last_scene_returns_only_last(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        self._write_episode(manifests_dir)

        resolver = AffectedRangeResolver()
        resolver.manifest = _make_manifest_service(manifests_dir)

        result = resolver.resolve("p1", "ep1", "scene_005", has_timeline_drift=True)
        assert [r["scene_id"] for r in result] == ["scene_005"]

    def test_unknown_scene_raises_value_error(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        self._write_episode(manifests_dir)

        resolver = AffectedRangeResolver()
        resolver.manifest = _make_manifest_service(manifests_dir)

        with pytest.raises(ValueError, match="Scene not found"):
            resolver.resolve("p1", "ep1", "scene_999", has_timeline_drift=True)

    def test_result_is_sorted_by_scene_id(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        # Write in reverse order to confirm sort
        for sid in ("scene_005", "scene_003", "scene_001", "scene_002", "scene_004"):
            _write_manifest(manifests_dir, "p1", "ep1", sid, {"duration_sec": 5.0})

        resolver = AffectedRangeResolver()
        resolver.manifest = _make_manifest_service(manifests_dir)

        result = resolver.resolve("p1", "ep1", "scene_003", has_timeline_drift=True)
        ids = [r["scene_id"] for r in result]
        assert ids == sorted(ids)


# ===========================================================================
# BurnInModeResolver
# ===========================================================================

from app.render.reassembly.burn_in_mode_resolver import BurnInModeResolver  # noqa: E402


class TestBurnInModeResolver:
    def test_default_mode_is_per_scene_burn_in(self):
        resolver = BurnInModeResolver()
        assert resolver.mode() == "per_scene_burn_in"

    def test_requires_range_false_when_no_drift(self):
        resolver = BurnInModeResolver()
        assert resolver.requires_affected_range_rebuild(has_timeline_drift=False) is False

    def test_requires_range_false_for_per_scene_mode_with_drift(self):
        resolver = BurnInModeResolver()
        with patch("app.render.reassembly.burn_in_mode_resolver.SUBTITLE_BURN_IN_MODE", "per_scene_burn_in"):
            assert resolver.requires_affected_range_rebuild(has_timeline_drift=True) is False

    def test_requires_range_true_for_global_mode_with_drift(self):
        resolver = BurnInModeResolver()
        with patch("app.render.assembly.subtitles.subtitle_mode.SUBTITLE_BURN_IN_MODE", "global_burn_in"), \
             patch("app.render.reassembly.burn_in_mode_resolver.SUBTITLE_BURN_IN_MODE", "global_burn_in"):
            assert resolver.requires_affected_range_rebuild(has_timeline_drift=True) is True

    def test_requires_only_changed_true_when_no_drift(self):
        resolver = BurnInModeResolver()
        assert resolver.requires_only_changed_scene(has_timeline_drift=False) is True

    def test_requires_only_changed_true_for_per_scene_mode_with_drift(self):
        resolver = BurnInModeResolver()
        with patch("app.render.reassembly.burn_in_mode_resolver.SUBTITLE_BURN_IN_MODE", "per_scene_burn_in"):
            assert resolver.requires_only_changed_scene(has_timeline_drift=True) is True

    def test_requires_only_changed_false_for_global_mode_with_drift(self):
        resolver = BurnInModeResolver()
        with patch("app.render.reassembly.burn_in_mode_resolver.SUBTITLE_BURN_IN_MODE", "global_burn_in"):
            assert resolver.requires_only_changed_scene(has_timeline_drift=True) is False


# ===========================================================================
# PerSceneSubtitleService
# ===========================================================================

from app.render.reassembly.per_scene_subtitle_service import PerSceneSubtitleService  # noqa: E402


class TestPerSceneSubtitleService:
    def test_rebuild_returns_correct_keys(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        _write_manifest(manifests_dir, "p1", "ep1", "scene_003", {
            "word_timings": [{"word": "Hi", "start_sec": 0.1, "end_sec": 0.5}],
        })

        svc = PerSceneSubtitleService()
        svc.manifest = _make_manifest_service(manifests_dir)

        with patch(
            "app.render.reassembly.per_scene_subtitle_service.write_visual_aware_karaoke_ass",
            return_value="/data/renders/subtitles/p1/ep1/scene_003.ass",
        ), patch("pathlib.Path.mkdir"):
            result = svc.rebuild_scene_subtitle("p1", "ep1", "scene_003")

        assert result["status"] == "scene_subtitle_rebuilt"
        assert result["scene_id"] == "scene_003"
        assert "scene_003.ass" in result["subtitle_path"]

    def test_rebuild_patches_manifest(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        _write_manifest(manifests_dir, "p1", "ep1", "scene_003", {
            "word_timings": [{"word": "Hi", "start_sec": 0.1, "end_sec": 0.5}],
        })

        svc = PerSceneSubtitleService()
        svc.manifest = _make_manifest_service(manifests_dir)

        with patch(
            "app.render.reassembly.per_scene_subtitle_service.write_visual_aware_karaoke_ass",
            return_value="/data/renders/subtitles/p1/ep1/scene_003.ass",
        ), patch("pathlib.Path.mkdir"):
            svc.rebuild_scene_subtitle("p1", "ep1", "scene_003")

        data = _read_manifest(manifests_dir, "p1", "ep1", "scene_003")
        assert data["subtitle_burn_in_mode"] == "per_scene_burn_in"
        assert "scene_003.ass" in data["subtitle_path"]

    def test_falls_back_to_global_word_timings(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        _write_manifest(manifests_dir, "p1", "ep1", "scene_003", {
            "global_word_timings": [{"word": "Hey", "start_sec": 5.0, "end_sec": 5.5}],
        })

        svc = PerSceneSubtitleService()
        svc.manifest = _make_manifest_service(manifests_dir)

        captured = {}

        def _capture(word_tracks, scene_placements, output_path):
            captured["words"] = word_tracks[0]["words"]
            return output_path

        with patch(
            "app.render.reassembly.per_scene_subtitle_service.write_visual_aware_karaoke_ass",
            side_effect=_capture,
        ), patch("pathlib.Path.mkdir"):
            svc.rebuild_scene_subtitle("p1", "ep1", "scene_003")

        assert captured["words"][0]["word"] == "Hey"

    def test_subtitle_path_is_scene_level_not_episode_level(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        _write_manifest(manifests_dir, "p1", "ep1", "scene_003", {"word_timings": []})

        svc = PerSceneSubtitleService()
        svc.manifest = _make_manifest_service(manifests_dir)

        with patch(
            "app.render.reassembly.per_scene_subtitle_service.write_visual_aware_karaoke_ass",
        ) as mock_write, patch("pathlib.Path.mkdir"):
            mock_write.side_effect = lambda word_tracks, scene_placements, output_path: output_path
            result = svc.rebuild_scene_subtitle("p1", "ep1", "scene_003")

        # Path must include episode_id subdirectory (scene-level, not episode-level)
        assert "ep1" in result["subtitle_path"]
        assert "scene_003.ass" in result["subtitle_path"]

    def test_rebuild_episode_returns_all_scenes(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        for sid in ("scene_001", "scene_002", "scene_003"):
            _write_manifest(manifests_dir, "p1", "ep1", sid, {"word_timings": []})

        svc = PerSceneSubtitleService()
        svc.manifest = _make_manifest_service(manifests_dir)

        with patch(
            "app.render.reassembly.per_scene_subtitle_service.write_visual_aware_karaoke_ass",
        ) as mock_write, patch("pathlib.Path.mkdir"):
            mock_write.side_effect = lambda word_tracks, scene_placements, output_path: output_path
            result = svc.rebuild_episode_per_scene_subtitles("p1", "ep1")

        assert result["status"] == "per_scene_subtitles_built"
        assert result["count"] == 3
        assert len(result["items"]) == 3

    def test_rebuild_episode_each_item_has_scene_id(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        for sid in ("scene_001", "scene_002"):
            _write_manifest(manifests_dir, "p1", "ep1", sid, {"word_timings": []})

        svc = PerSceneSubtitleService()
        svc.manifest = _make_manifest_service(manifests_dir)

        with patch(
            "app.render.reassembly.per_scene_subtitle_service.write_visual_aware_karaoke_ass",
        ) as mock_write, patch("pathlib.Path.mkdir"):
            mock_write.side_effect = lambda word_tracks, scene_placements, output_path: output_path
            result = svc.rebuild_episode_per_scene_subtitles("p1", "ep1")

        scene_ids = {item["scene_id"] for item in result["items"]}
        assert scene_ids == {"scene_001", "scene_002"}

    def test_rebuild_episode_empty_episode(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        svc = PerSceneSubtitleService()
        svc.manifest = _make_manifest_service(manifests_dir)

        result = svc.rebuild_episode_per_scene_subtitles("p1", "ep_empty")

        assert result["status"] == "per_scene_subtitles_built"
        assert result["count"] == 0
        assert result["items"] == []


# ===========================================================================
# SmartReassemblyService — affected range behaviour
# ===========================================================================

from app.render.reassembly.schemas import SmartReassemblyRequest  # noqa: E402
from app.render.reassembly.smart_reassembly_service import SmartReassemblyService  # noqa: E402


def _write_5_scene_episode(manifests_dir: str, drift_on: str = "scene_003") -> None:
    for i, sid in enumerate(
        ("scene_001", "scene_002", "scene_003", "scene_004", "scene_005"), start=1
    ):
        data: Dict[str, Any] = {
            "scene_id": sid,
            "video_path": f"/v/{sid}.mp4",
            "audio_path": f"/a/{sid}.wav",
            "duration_sec": 8.0,
            "word_timings": [],
        }
        if sid == drift_on:
            data["previous_duration_sec"] = 5.0  # was 5s, now 8s → +3s drift
        _write_manifest(manifests_dir, "p1", "ep1", sid, data)


class TestSmartReassemblyAffectedRange:
    def _req(self, changed: str = "scene_003") -> SmartReassemblyRequest:
        return SmartReassemblyRequest(
            project_id="p1",
            episode_id="ep1",
            changed_scene_id=changed,
        )

    def _mock_chunk(self, scene_id: str, duration: float = 8.0) -> Dict[str, Any]:
        return {"scene_id": scene_id, "chunk_path": f"/chunks/{scene_id}.mp4", "duration_sec": duration}

    def _make_svc(self, manifests_dir: str, chunks_dir: str) -> SmartReassemblyService:
        return SmartReassemblyService(
            manifest_base_dir=manifests_dir,
            chunk_base_dir=chunks_dir,
        )

    def test_no_drift_rebuilds_only_changed_scene(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        chunks_dir = str(tmp_path / "chunks")
        # No drift: previous_duration_sec == duration_sec
        for sid in ("scene_001", "scene_002", "scene_003", "scene_004", "scene_005"):
            _write_manifest(manifests_dir, "p1", "ep1", sid, {
                "scene_id": sid,
                "video_path": f"/v/{sid}.mp4",
                "audio_path": f"/a/{sid}.wav",
                "duration_sec": 5.0,
                "previous_duration_sec": 5.0,
                "word_timings": [],
            })

        svc = self._make_svc(manifests_dir, chunks_dir)

        mock_final = {"status": "succeeded", "output_path": "/final/ep1.mp4"}

        def _mock_build(project_id, episode_id, scene_manifest):
            return self._mock_chunk(scene_manifest["scene_id"])

        with patch.object(svc._chunk_builder, "build_scene_chunk", side_effect=_mock_build), \
             patch.object(svc._finalizer, "concat_chunks", return_value=mock_final), \
             patch.object(svc._timeline_rebuilder, "rebuild_episode_offsets") as mock_tl, \
             patch.object(svc._subtitle_rebuilder, "rebuild_episode_subtitles") as mock_sub, \
             patch.object(svc._per_scene_subtitles, "rebuild_scene_subtitle") as mock_ps:
            result = svc.reassemble(self._req("scene_003"))

        assert result["rebuilt_scene_ids"] == ["scene_003"]
        assert result["rebuilt_count"] == 1
        mock_tl.assert_not_called()
        mock_sub.assert_not_called()
        mock_ps.assert_not_called()

    def test_drift_with_per_scene_mode_rebuilds_only_changed(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        chunks_dir = str(tmp_path / "chunks")
        _write_5_scene_episode(manifests_dir, drift_on="scene_003")

        svc = self._make_svc(manifests_dir, chunks_dir)

        mock_final = {"status": "succeeded", "output_path": "/final/ep1.mp4"}
        mock_per_scene_sub = {
            "status": "scene_subtitle_rebuilt",
            "scene_id": "scene_003",
            "subtitle_path": "/subs/ep1/scene_003.ass",
        }
        mock_tl = {"total_duration_sec": 35.0, "timeline": []}

        def _mock_build(project_id, episode_id, scene_manifest):
            return self._mock_chunk(scene_manifest["scene_id"])

        with patch.object(svc._chunk_builder, "build_scene_chunk", side_effect=_mock_build), \
             patch.object(svc._finalizer, "concat_chunks", return_value=mock_final), \
             patch.object(svc._timeline_rebuilder, "rebuild_episode_offsets", return_value=mock_tl), \
             patch.object(svc._per_scene_subtitles, "rebuild_scene_subtitle", return_value=mock_per_scene_sub), \
             patch.object(svc._subtitle_rebuilder, "rebuild_episode_subtitles") as mock_global_sub, \
             patch("app.render.reassembly.burn_in_mode_resolver.SUBTITLE_BURN_IN_MODE", "per_scene_burn_in"):
            result = svc.reassemble(self._req("scene_003"))

        assert result["timeline_drift"]["has_drift"] is True
        assert result["rebuilt_scene_ids"] == ["scene_003"]
        assert result["rebuilt_count"] == 1
        mock_global_sub.assert_not_called()

    def test_drift_with_global_mode_rebuilds_affected_range(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        chunks_dir = str(tmp_path / "chunks")
        _write_5_scene_episode(manifests_dir, drift_on="scene_003")

        svc = self._make_svc(manifests_dir, chunks_dir)

        mock_final = {"status": "succeeded", "output_path": "/final/ep1.mp4"}
        mock_episode_sub = {
            "status": "subtitle_rebuilt",
            "subtitle_path": "/subs/ep1.ass",
            "scene_count": 5,
            "word_track_count": 5,
        }
        mock_tl = {"total_duration_sec": 35.0, "timeline": []}

        def _mock_build(project_id, episode_id, scene_manifest):
            return self._mock_chunk(scene_manifest["scene_id"])

        with patch.object(svc._chunk_builder, "build_scene_chunk", side_effect=_mock_build), \
             patch.object(svc._finalizer, "concat_chunks", return_value=mock_final), \
             patch.object(svc._timeline_rebuilder, "rebuild_episode_offsets", return_value=mock_tl), \
             patch.object(svc._subtitle_rebuilder, "rebuild_episode_subtitles", return_value=mock_episode_sub), \
             patch.object(svc._per_scene_subtitles, "rebuild_scene_subtitle") as mock_ps, \
             patch("app.render.reassembly.burn_in_mode_resolver.SUBTITLE_BURN_IN_MODE", "global_burn_in"):
            result = svc.reassemble(self._req("scene_003"))

        assert result["timeline_drift"]["has_drift"] is True
        assert result["rebuilt_scene_ids"] == ["scene_003", "scene_004", "scene_005"]
        assert result["rebuilt_count"] == 3
        mock_ps.assert_not_called()

    def test_affected_manifests_patched_with_affected_flag(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        chunks_dir = str(tmp_path / "chunks")
        _write_5_scene_episode(manifests_dir, drift_on="scene_003")

        svc = self._make_svc(manifests_dir, chunks_dir)

        mock_final = {"status": "succeeded", "output_path": "/final/ep1.mp4"}
        mock_episode_sub = {
            "status": "subtitle_rebuilt",
            "subtitle_path": "/subs/ep1.ass",
            "scene_count": 5,
            "word_track_count": 5,
        }
        mock_tl = {"total_duration_sec": 35.0, "timeline": []}

        def _mock_build(project_id, episode_id, scene_manifest):
            return self._mock_chunk(scene_manifest["scene_id"])

        with patch.object(svc._chunk_builder, "build_scene_chunk", side_effect=_mock_build), \
             patch.object(svc._finalizer, "concat_chunks", return_value=mock_final), \
             patch.object(svc._timeline_rebuilder, "rebuild_episode_offsets", return_value=mock_tl), \
             patch.object(svc._subtitle_rebuilder, "rebuild_episode_subtitles", return_value=mock_episode_sub), \
             patch("app.render.reassembly.burn_in_mode_resolver.SUBTITLE_BURN_IN_MODE", "global_burn_in"):
            svc.reassemble(self._req("scene_003"))

        s3 = _read_manifest(manifests_dir, "p1", "ep1", "scene_003")
        s4 = _read_manifest(manifests_dir, "p1", "ep1", "scene_004")
        s5 = _read_manifest(manifests_dir, "p1", "ep1", "scene_005")

        assert s3["affected_by_timeline_drift"] is False
        assert s4["affected_by_timeline_drift"] is True
        assert s5["affected_by_timeline_drift"] is True

    def test_unchanged_scenes_not_rebuilt_in_global_mode(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        chunks_dir = str(tmp_path / "chunks")
        _write_5_scene_episode(manifests_dir, drift_on="scene_003")

        svc = self._make_svc(manifests_dir, chunks_dir)

        mock_final = {"status": "succeeded", "output_path": "/final/ep1.mp4"}
        mock_episode_sub = {
            "status": "subtitle_rebuilt",
            "subtitle_path": "/subs/ep1.ass",
            "scene_count": 5,
            "word_track_count": 5,
        }
        mock_tl = {"total_duration_sec": 35.0, "timeline": []}

        def _mock_build(project_id, episode_id, scene_manifest):
            return self._mock_chunk(scene_manifest["scene_id"])

        with patch.object(svc._chunk_builder, "build_scene_chunk", side_effect=_mock_build), \
             patch.object(svc._finalizer, "concat_chunks", return_value=mock_final), \
             patch.object(svc._timeline_rebuilder, "rebuild_episode_offsets", return_value=mock_tl), \
             patch.object(svc._subtitle_rebuilder, "rebuild_episode_subtitles", return_value=mock_episode_sub), \
             patch("app.render.reassembly.burn_in_mode_resolver.SUBTITLE_BURN_IN_MODE", "global_burn_in"):
            result = svc.reassemble(self._req("scene_003"))

        assert "scene_001" not in result["rebuilt_scene_ids"]
        assert "scene_002" not in result["rebuilt_scene_ids"]

    def test_result_contains_required_keys(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        chunks_dir = str(tmp_path / "chunks")
        _write_5_scene_episode(manifests_dir, drift_on="scene_003")

        svc = self._make_svc(manifests_dir, chunks_dir)

        mock_final = {"status": "succeeded", "output_path": "/final/ep1.mp4"}
        mock_tl = {"total_duration_sec": 35.0, "timeline": []}
        mock_per_scene_sub = {"status": "scene_subtitle_rebuilt", "scene_id": "scene_003", "subtitle_path": "/s.ass"}

        def _mock_build(project_id, episode_id, scene_manifest):
            return self._mock_chunk(scene_manifest["scene_id"])

        with patch.object(svc._chunk_builder, "build_scene_chunk", side_effect=_mock_build), \
             patch.object(svc._finalizer, "concat_chunks", return_value=mock_final), \
             patch.object(svc._timeline_rebuilder, "rebuild_episode_offsets", return_value=mock_tl), \
             patch.object(svc._per_scene_subtitles, "rebuild_scene_subtitle", return_value=mock_per_scene_sub), \
             patch("app.render.reassembly.burn_in_mode_resolver.SUBTITLE_BURN_IN_MODE", "per_scene_burn_in"):
            result = svc.reassemble(self._req("scene_003"))

        required = {
            "status", "changed_scene_id", "timeline_drift",
            "timeline_report", "subtitle_report",
            "rebuilt_scene_ids", "rebuilt_count", "final",
        }
        assert required.issubset(result.keys())
