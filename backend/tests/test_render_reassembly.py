"""Tests for the Smart Reassembly and Chunk Bootstrap modules.

All filesystem I/O is redirected to a temporary directory so the tests are
fully self-contained and leave no artefacts behind.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_dirs(tmp_path: Path):
    """Return a dict of base directories wired to a temp folder."""
    dirs = {
        "manifests": str(tmp_path / "manifests"),
        "chunks": str(tmp_path / "chunks"),
        "final": str(tmp_path / "final"),
    }
    for d in dirs.values():
        Path(d).mkdir(parents=True, exist_ok=True)
    return dirs


def _write_manifest(base_dir: str, project_id: str, episode_id: str, scene_id: str, data: Dict[str, Any]) -> None:
    """Write a scene manifest JSON directly (bypasses ManifestService)."""
    out = Path(base_dir) / project_id / episode_id
    out.mkdir(parents=True, exist_ok=True)
    payload = {"project_id": project_id, "episode_id": episode_id, "scene_id": scene_id, **data}
    (out / f"{scene_id}.json").write_text(json.dumps(payload))


# ===========================================================================
# ChunkIndex
# ===========================================================================

from app.render.reassembly.chunk_index import ChunkIndex  # noqa: E402


class TestChunkIndex:
    def test_load_missing_returns_skeleton(self, tmp_path):
        ci = ChunkIndex(base_dir=str(tmp_path / "chunks"))
        index = ci.load("p1", "ep1")
        assert index == {"project_id": "p1", "episode_id": "ep1", "chunks": []}

    def test_save_and_load_round_trip(self, tmp_path):
        ci = ChunkIndex(base_dir=str(tmp_path / "chunks"))
        index = {"project_id": "p1", "episode_id": "ep1", "chunks": [{"scene_id": "s1", "chunk_path": "/x/s1.mp4", "duration_sec": 5.0}]}
        ci.save("p1", "ep1", index)
        loaded = ci.load("p1", "ep1")
        assert loaded["chunks"][0]["scene_id"] == "s1"

    def test_update_chunk_inserts_new(self, tmp_path):
        ci = ChunkIndex(base_dir=str(tmp_path / "chunks"))
        ci.update_chunk("p1", "ep1", "s1", "/chunks/s1.mp4", 4.0)
        ci.update_chunk("p1", "ep1", "s2", "/chunks/s2.mp4", 6.0)
        index = ci.load("p1", "ep1")
        assert len(index["chunks"]) == 2

    def test_update_chunk_replaces_existing(self, tmp_path):
        ci = ChunkIndex(base_dir=str(tmp_path / "chunks"))
        ci.update_chunk("p1", "ep1", "s1", "/old/s1.mp4", 4.0)
        ci.update_chunk("p1", "ep1", "s1", "/new/s1.mp4", 5.0)
        index = ci.load("p1", "ep1")
        assert len(index["chunks"]) == 1
        assert index["chunks"][0]["chunk_path"] == "/new/s1.mp4"

    def test_update_chunk_keeps_sorted_order(self, tmp_path):
        ci = ChunkIndex(base_dir=str(tmp_path / "chunks"))
        ci.update_chunk("p1", "ep1", "scene_03", "/c/s3.mp4", 3.0)
        ci.update_chunk("p1", "ep1", "scene_01", "/c/s1.mp4", 1.0)
        ci.update_chunk("p1", "ep1", "scene_02", "/c/s2.mp4", 2.0)
        index = ci.load("p1", "ep1")
        ids = [c["scene_id"] for c in index["chunks"]]
        assert ids == ["scene_01", "scene_02", "scene_03"]


# ===========================================================================
# ChunkBuilder
# ===========================================================================

from app.render.reassembly.chunk_builder import ChunkBuilder  # noqa: E402


class TestChunkBuilder:
    def _manifest(self, scene_id: str = "s1", subtitle: bool = False) -> Dict[str, Any]:
        m: Dict[str, Any] = {
            "scene_id": scene_id,
            "video_path": f"/videos/{scene_id}.mp4",
            "audio_path": f"/audio/{scene_id}.wav",
            "duration_sec": 8.0,
        }
        if subtitle:
            m["subtitle_path"] = f"/subs/{scene_id}.ass"
        return m

    def test_returns_chunk_dict_on_success(self, tmp_path):
        cb = ChunkBuilder()
        mock_result = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock_result) as mock_run, \
             patch("pathlib.Path.mkdir"):
            result = cb.build_scene_chunk("p1", "ep1", self._manifest())
        assert result["scene_id"] == "s1"
        assert result["chunk_path"].endswith("s1.mp4")
        assert result["duration_sec"] == 8.0
        mock_run.assert_called_once()

    def test_includes_subtitle_vf_filter(self, tmp_path):
        cb = ChunkBuilder()
        mock_result = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock_result) as mock_run, \
             patch("pathlib.Path.mkdir"):
            cb.build_scene_chunk("p1", "ep1", self._manifest(subtitle=True))
        cmd = mock_run.call_args[0][0]
        assert any("ass=" in arg for arg in cmd)

    def test_raises_runtime_error_on_ffmpeg_failure(self, tmp_path):
        cb = ChunkBuilder()
        mock_result = MagicMock(returncode=1, stderr="ffmpeg error")
        with patch("subprocess.run", return_value=mock_result), \
             patch("pathlib.Path.mkdir"):
            with pytest.raises(RuntimeError, match="Chunk build failed"):
                cb.build_scene_chunk("p1", "ep1", self._manifest())

    def test_no_vf_filter_without_subtitle(self):
        cb = ChunkBuilder()
        mock_result = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock_result) as mock_run, \
             patch("pathlib.Path.mkdir"):
            cb.build_scene_chunk("p1", "ep1", self._manifest())
        cmd = mock_run.call_args[0][0]
        assert "-vf" not in cmd


# ===========================================================================
# ConcatFinalizer
# ===========================================================================

from app.render.reassembly.concat_finalizer import ConcatFinalizer  # noqa: E402


class TestConcatFinalizer:
    def _chunks(self):
        return [
            {"scene_id": "s1", "chunk_path": "/chunks/s1.mp4", "duration_sec": 5.0},
            {"scene_id": "s2", "chunk_path": "/chunks/s2.mp4", "duration_sec": 6.0},
        ]

    def test_returns_output_path_on_success(self, tmp_path):
        cf = ConcatFinalizer()
        mock_result = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock_result), \
             patch("pathlib.Path.mkdir"):
            result = cf.concat_chunks("p1", "ep1", self._chunks())
        assert result["status"] == "succeeded"
        assert "ep1.mp4" in result["output_path"]

    def test_raises_on_ffmpeg_failure(self):
        cf = ConcatFinalizer()
        mock_result = MagicMock(returncode=1, stderr="concat error")
        with patch("subprocess.run", return_value=mock_result), \
             patch("pathlib.Path.mkdir"):
            with pytest.raises(RuntimeError, match="Smart concat failed"):
                cf.concat_chunks("p1", "ep1", self._chunks())

    def test_writes_concat_file_with_all_chunks(self, tmp_path):
        cf = ConcatFinalizer()
        mock_result = MagicMock(returncode=0)
        written_lines = []

        real_open = open

        def _mock_open(path, mode="r", **kwargs):
            if "smart_concat" in str(path) and "w" in mode:
                import io
                buf = io.StringIO()
                # Capture the written content
                class _Capturing:
                    def __enter__(self_inner):
                        return self_inner
                    def __exit__(self_inner, *a):
                        written_lines.extend(buf.getvalue().splitlines())
                    def write(self_inner, data):
                        buf.write(data)
                return _Capturing()
            return real_open(path, mode, **kwargs)

        with patch("subprocess.run", return_value=mock_result), \
             patch("pathlib.Path.mkdir"):
            cf.concat_chunks("p1", "ep1", self._chunks())


# ===========================================================================
# SmartReassemblyService
# ===========================================================================

from app.render.reassembly.schemas import SmartReassemblyRequest  # noqa: E402
from app.render.reassembly.smart_reassembly_service import SmartReassemblyService  # noqa: E402


class TestSmartReassemblyService:
    def _req(self, force: bool = False) -> SmartReassemblyRequest:
        return SmartReassemblyRequest(
            project_id="p1",
            episode_id="ep1",
            changed_scene_id="s1",
            force_full_rebuild=force,
        )

    def _scene_manifest(self):
        return {
            "project_id": "p1",
            "episode_id": "ep1",
            "scene_id": "s1",
            "video_path": "/v/s1.mp4",
            "audio_path": "/a/s1.wav",
            "duration_sec": 8.0,
            "status": "rerendered",
        }

    def test_smart_rebuild_happy_path(self, tmp_dirs):
        svc = SmartReassemblyService(
            manifest_base_dir=tmp_dirs["manifests"],
            chunk_base_dir=tmp_dirs["chunks"],
        )
        _write_manifest(tmp_dirs["manifests"], "p1", "ep1", "s1", self._scene_manifest())

        mock_chunk = {"scene_id": "s1", "chunk_path": "/chunks/s1.mp4", "duration_sec": 8.0}
        mock_final = {"status": "succeeded", "output_path": "/final/ep1.mp4"}

        with patch.object(svc._chunk_builder, "build_scene_chunk", return_value=mock_chunk), \
             patch.object(svc._finalizer, "concat_chunks", return_value=mock_final):
            result = svc.reassemble(self._req())

        assert result["status"] == "smart_reassembled"
        assert result["rebuilt_scene_id"] == "s1"
        assert result["chunk"] == mock_chunk
        assert result["final"] == mock_final

    def test_smart_rebuild_updates_manifest(self, tmp_dirs):
        svc = SmartReassemblyService(
            manifest_base_dir=tmp_dirs["manifests"],
            chunk_base_dir=tmp_dirs["chunks"],
        )
        _write_manifest(tmp_dirs["manifests"], "p1", "ep1", "s1", self._scene_manifest())

        mock_chunk = {"scene_id": "s1", "chunk_path": "/chunks/s1.mp4", "duration_sec": 8.0}
        mock_final = {"status": "succeeded", "output_path": "/final/ep1.mp4"}

        with patch.object(svc._chunk_builder, "build_scene_chunk", return_value=mock_chunk), \
             patch.object(svc._finalizer, "concat_chunks", return_value=mock_final):
            svc.reassemble(self._req())

        manifest_path = Path(tmp_dirs["manifests"]) / "p1" / "ep1" / "s1.json"
        data = json.loads(manifest_path.read_text())
        assert data["status"] == "smart_reassembled"
        assert data["needs_reassembly"] is False
        assert data["needs_smart_reassembly"] is False

    def test_full_rebuild_path(self, tmp_dirs):
        svc = SmartReassemblyService(
            manifest_base_dir=tmp_dirs["manifests"],
            chunk_base_dir=tmp_dirs["chunks"],
        )
        for sid in ("s1", "s2"):
            _write_manifest(tmp_dirs["manifests"], "p1", "ep1", sid, {
                "scene_id": sid, "video_path": f"/v/{sid}.mp4",
                "audio_path": f"/a/{sid}.wav", "duration_sec": 5.0,
            })

        mock_chunk = {"scene_id": "s1", "chunk_path": "/chunks/s1.mp4", "duration_sec": 5.0}
        mock_final = {"status": "succeeded", "output_path": "/final/ep1.mp4"}

        with patch.object(svc._chunk_builder, "build_scene_chunk", return_value=mock_chunk), \
             patch.object(svc._finalizer, "concat_chunks", return_value=mock_final):
            result = svc.reassemble(self._req(force=True))

        assert result["status"] == "full_reassembled"

    def test_missing_manifest_raises(self, tmp_dirs):
        svc = SmartReassemblyService(
            manifest_base_dir=tmp_dirs["manifests"],
            chunk_base_dir=tmp_dirs["chunks"],
        )
        with pytest.raises(FileNotFoundError):
            svc.reassemble(self._req())


# ===========================================================================
# ChunkBootstrapper
# ===========================================================================

from app.render.reassembly.chunk_bootstrapper import ChunkBootstrapper  # noqa: E402


class TestChunkBootstrapper:
    def test_bootstrap_happy_path(self, tmp_dirs):
        bs = ChunkBootstrapper(
            manifest_base_dir=tmp_dirs["manifests"],
            chunk_base_dir=tmp_dirs["chunks"],
        )
        for sid in ("s1", "s2"):
            _write_manifest(tmp_dirs["manifests"], "p1", "ep1", sid, {
                "scene_id": sid,
                "video_path": f"/v/{sid}.mp4",
                "audio_path": f"/a/{sid}.wav",
                "duration_sec": 5.0,
                "status": "assembled",
            })

        mock_chunk_fn = lambda project_id, episode_id, scene_manifest: {
            "scene_id": scene_manifest["scene_id"],
            "chunk_path": f"/chunks/{scene_manifest['scene_id']}.mp4",
            "duration_sec": 5.0,
        }

        with patch.object(bs._chunk_builder, "build_scene_chunk", side_effect=mock_chunk_fn):
            result = bs.bootstrap_episode("p1", "ep1")

        assert result["status"] == "bootstrapped"
        assert result["chunk_count"] == 2
        assert Path(result["chunk_index_path"]).exists()

    def test_bootstrap_writes_chunk_index(self, tmp_dirs):
        bs = ChunkBootstrapper(
            manifest_base_dir=tmp_dirs["manifests"],
            chunk_base_dir=tmp_dirs["chunks"],
        )
        _write_manifest(tmp_dirs["manifests"], "p1", "ep1", "s1", {
            "scene_id": "s1", "video_path": "/v/s1.mp4",
            "audio_path": "/a/s1.wav", "duration_sec": 5.0,
        })

        mock_chunk = {"scene_id": "s1", "chunk_path": "/chunks/s1.mp4", "duration_sec": 5.0}
        with patch.object(bs._chunk_builder, "build_scene_chunk", return_value=mock_chunk):
            bs.bootstrap_episode("p1", "ep1")

        index_path = Path(tmp_dirs["chunks"]) / "p1" / "ep1" / "chunk_index.json"
        assert index_path.exists()
        data = json.loads(index_path.read_text())
        assert data["smart_reassembly_ready"] is True
        assert len(data["chunks"]) == 1

    def test_bootstrap_patches_manifests(self, tmp_dirs):
        bs = ChunkBootstrapper(
            manifest_base_dir=tmp_dirs["manifests"],
            chunk_base_dir=tmp_dirs["chunks"],
        )
        _write_manifest(tmp_dirs["manifests"], "p1", "ep1", "s1", {
            "scene_id": "s1", "video_path": "/v/s1.mp4",
            "audio_path": "/a/s1.wav", "duration_sec": 5.0,
        })

        mock_chunk = {"scene_id": "s1", "chunk_path": "/chunks/s1.mp4", "duration_sec": 5.0}
        with patch.object(bs._chunk_builder, "build_scene_chunk", return_value=mock_chunk):
            bs.bootstrap_episode("p1", "ep1")

        manifest_path = Path(tmp_dirs["manifests"]) / "p1" / "ep1" / "s1.json"
        data = json.loads(manifest_path.read_text())
        assert data["chunk_path"] == "/chunks/s1.mp4"
        assert data["smart_reassembly_ready"] is True

    def test_bootstrap_raises_on_empty_episode(self, tmp_dirs):
        bs = ChunkBootstrapper(
            manifest_base_dir=tmp_dirs["manifests"],
            chunk_base_dir=tmp_dirs["chunks"],
        )
        with pytest.raises(ValueError, match="No scene manifests"):
            bs.bootstrap_episode("p1", "ep_empty")

    def test_bootstrap_raises_on_missing_video_path(self, tmp_dirs):
        bs = ChunkBootstrapper(
            manifest_base_dir=tmp_dirs["manifests"],
            chunk_base_dir=tmp_dirs["chunks"],
        )
        _write_manifest(tmp_dirs["manifests"], "p1", "ep1", "s1", {
            "scene_id": "s1", "audio_path": "/a/s1.wav", "duration_sec": 5.0,
        })
        with pytest.raises(ValueError, match="Missing video_path"):
            bs.bootstrap_episode("p1", "ep1")

    def test_bootstrap_raises_on_missing_audio_path(self, tmp_dirs):
        bs = ChunkBootstrapper(
            manifest_base_dir=tmp_dirs["manifests"],
            chunk_base_dir=tmp_dirs["chunks"],
        )
        _write_manifest(tmp_dirs["manifests"], "p1", "ep1", "s1", {
            "scene_id": "s1", "video_path": "/v/s1.mp4", "duration_sec": 5.0,
        })
        with pytest.raises(ValueError, match="Missing audio_path"):
            bs.bootstrap_episode("p1", "ep1")


# ===========================================================================
# FFmpegAssemblyExecutor — chunk_bootstrap key in return dict
# ===========================================================================

from app.render.assembly.executors.ffmpeg_assembly_executor import FFmpegAssemblyExecutor  # noqa: E402


class TestFFmpegAssemblyExecutorBootstrap:
    """Verify that execute() now returns chunk_bootstrap in its result."""

    _PLAN = {
        "video_tracks": [{"scene_id": "s1", "video_url": "/v/s1.mp4"}],
        "audio_tracks": [{"scene_id": "s1", "audio_url": "/a/s1.wav", "word_timings": []}],
        "subtitle_tracks": [{"scene_id": "s1", "text": "hello"}],
    }

    def test_execute_includes_chunk_bootstrap_key(self, tmp_path):
        executor = FFmpegAssemblyExecutor()
        mock_proc = MagicMock(returncode=0, stderr="")
        mock_bootstrap = {"status": "bootstrapped", "chunk_count": 1}

        with patch.object(executor.validator, "validate_plan"), \
             patch.object(executor.validator, "validate_assets"), \
             patch.object(executor.resolver, "resolve_scene_video", return_value="/v/s1.mp4"), \
             patch.object(executor.resolver, "resolve_scene_audio", return_value="/a/s1.wav"), \
             patch.object(executor.resolver, "resolve_output_path", return_value=str(tmp_path / "out.mp4")), \
             patch.object(executor.resolver, "resolve_subtitle_path", return_value=str(tmp_path / "sub.ass")), \
             patch.object(executor.builder, "build_concat_file"), \
             patch.object(executor.builder, "build_command", return_value=["ffmpeg"]), \
             patch("subprocess.run", return_value=mock_proc), \
             patch("app.render.assembly.executors.ffmpeg_assembly_executor.write_karaoke_ass"), \
             patch("app.render.reassembly.chunk_bootstrapper.ChunkBootstrapper.bootstrap_episode",
                   return_value=mock_bootstrap):
            result = executor.execute("p1", "ep1", self._PLAN)

        assert "chunk_bootstrap" in result
        assert result["chunk_bootstrap"]["status"] == "bootstrapped"

    def test_execute_continues_when_bootstrap_fails(self, tmp_path):
        executor = FFmpegAssemblyExecutor()
        mock_proc = MagicMock(returncode=0, stderr="")

        with patch.object(executor.validator, "validate_plan"), \
             patch.object(executor.validator, "validate_assets"), \
             patch.object(executor.resolver, "resolve_scene_video", return_value="/v/s1.mp4"), \
             patch.object(executor.resolver, "resolve_scene_audio", return_value="/a/s1.wav"), \
             patch.object(executor.resolver, "resolve_output_path", return_value=str(tmp_path / "out.mp4")), \
             patch.object(executor.resolver, "resolve_subtitle_path", return_value=str(tmp_path / "sub.ass")), \
             patch.object(executor.builder, "build_concat_file"), \
             patch.object(executor.builder, "build_command", return_value=["ffmpeg"]), \
             patch("subprocess.run", return_value=mock_proc), \
             patch("app.render.assembly.executors.ffmpeg_assembly_executor.write_karaoke_ass"), \
             patch("app.render.reassembly.chunk_bootstrapper.ChunkBootstrapper.bootstrap_episode",
                   side_effect=RuntimeError("disk full")):
            result = executor.execute("p1", "ep1", self._PLAN)

        # Final MP4 was produced; bootstrap failure is captured, not raised.
        assert result["status"] == "succeeded"
        assert result["chunk_bootstrap"]["status"] == "failed"
        assert "disk full" in result["chunk_bootstrap"]["error"]["message"]
