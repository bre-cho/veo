"""Unit tests for the Scene Asset Manifest module."""
from __future__ import annotations

import json
import os
import tempfile

import pytest


# ---------------------------------------------------------------------------
# ManifestWriter
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestManifestWriter:
    def _writer(self, tmp_dir: str):
        from app.render.manifest.manifest_writer import ManifestWriter
        return ManifestWriter(base_dir=tmp_dir)

    def test_write_creates_file(self, tmp_path):
        w = self._writer(str(tmp_path))
        path = w.write_scene_manifest({
            "project_id": "p1", "episode_id": "e1", "scene_id": "s1", "status": "created",
        })
        assert os.path.exists(path)

    def test_write_sets_updated_at(self, tmp_path):
        w = self._writer(str(tmp_path))
        m = {"project_id": "p1", "episode_id": "e1", "scene_id": "s1"}
        w.write_scene_manifest(m)
        assert "updated_at" in m

    def test_write_json_roundtrip(self, tmp_path):
        w = self._writer(str(tmp_path))
        manifest = {
            "project_id": "p1",
            "episode_id": "e1",
            "scene_id": "opening",
            "status": "rendering",
            "voiceover_text": "It already happened.",
        }
        path = w.write_scene_manifest(manifest)
        with open(path, encoding="utf-8") as fh:
            loaded = json.load(fh)
        assert loaded["voiceover_text"] == "It already happened."

    def test_patch_creates_new_when_absent(self, tmp_path):
        w = self._writer(str(tmp_path))
        w.patch_scene_manifest("p1", "e1", "s1", {"status": "rendering"})
        path = w._path("p1", "e1", "s1")
        assert path.exists()

    def test_patch_merges_into_existing(self, tmp_path):
        w = self._writer(str(tmp_path))
        w.write_scene_manifest({
            "project_id": "p1", "episode_id": "e1", "scene_id": "s1",
            "status": "rendering", "voiceover_text": "hello",
        })
        w.patch_scene_manifest("p1", "e1", "s1", {"status": "succeeded", "video_path": "/v.mp4"})
        path = w._path("p1", "e1", "s1")
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["status"] == "succeeded"
        assert data["voiceover_text"] == "hello"
        assert data["video_path"] == "/v.mp4"

    def test_patch_stamps_identity_keys(self, tmp_path):
        w = self._writer(str(tmp_path))
        w.patch_scene_manifest("p2", "e2", "s2", {"status": "x"})
        with open(w._path("p2", "e2", "s2"), encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["project_id"] == "p2"
        assert data["episode_id"] == "e2"
        assert data["scene_id"] == "s2"


# ---------------------------------------------------------------------------
# ManifestReader
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestManifestReader:
    def _writer(self, tmp_dir: str):
        from app.render.manifest.manifest_writer import ManifestWriter
        return ManifestWriter(base_dir=tmp_dir)

    def _reader(self, tmp_dir: str):
        from app.render.manifest.manifest_reader import ManifestReader
        return ManifestReader(base_dir=tmp_dir)

    def test_read_returns_correct_data(self, tmp_path):
        w = self._writer(str(tmp_path))
        w.write_scene_manifest({
            "project_id": "p1", "episode_id": "e1", "scene_id": "s1",
            "status": "assembled", "voiceover_text": "test",
        })
        r = self._reader(str(tmp_path))
        data = r.read_scene_manifest("p1", "e1", "s1")
        assert data["status"] == "assembled"
        assert data["voiceover_text"] == "test"

    def test_read_raises_when_not_found(self, tmp_path):
        r = self._reader(str(tmp_path))
        with pytest.raises(FileNotFoundError):
            r.read_scene_manifest("p1", "e1", "nonexistent")

    def test_list_episode_returns_empty_for_unknown_episode(self, tmp_path):
        r = self._reader(str(tmp_path))
        result = r.list_episode_manifests("px", "ex")
        assert result == []

    def test_list_episode_returns_all_scenes(self, tmp_path):
        w = self._writer(str(tmp_path))
        for sid in ("s1", "s2", "s3"):
            w.write_scene_manifest({
                "project_id": "p1", "episode_id": "e1", "scene_id": sid,
            })
        r = self._reader(str(tmp_path))
        items = r.list_episode_manifests("p1", "e1")
        assert len(items) == 3
        scene_ids = {m["scene_id"] for m in items}
        assert scene_ids == {"s1", "s2", "s3"}

    def test_list_episode_is_sorted(self, tmp_path):
        w = self._writer(str(tmp_path))
        for sid in ("s2", "s1", "s3"):
            w.write_scene_manifest({
                "project_id": "p1", "episode_id": "e1", "scene_id": sid,
            })
        r = self._reader(str(tmp_path))
        items = r.list_episode_manifests("p1", "e1")
        ids = [m["scene_id"] for m in items]
        assert ids == sorted(ids)


# ---------------------------------------------------------------------------
# ManifestService
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestManifestService:
    def _service(self, tmp_path):
        from app.render.manifest.manifest_service import ManifestService
        return ManifestService(base_dir=str(tmp_path))

    def test_patch_then_get_roundtrip(self, tmp_path):
        svc = self._service(tmp_path)
        svc.patch_scene("p1", "e1", "s1", {"status": "rendering", "voiceover_text": "hello"})
        svc.patch_scene("p1", "e1", "s1", {"status": "succeeded", "video_path": "/v.mp4"})
        data = svc.get_scene("p1", "e1", "s1")
        assert data["status"] == "succeeded"
        assert data["voiceover_text"] == "hello"
        assert data["video_path"] == "/v.mp4"

    def test_list_episode_returns_patched_scenes(self, tmp_path):
        svc = self._service(tmp_path)
        for sid in ("a", "b"):
            svc.patch_scene("p1", "e1", sid, {"status": "assembled"})
        items = svc.list_episode("p1", "e1")
        assert len(items) == 2

    def test_get_raises_for_missing_scene(self, tmp_path):
        svc = self._service(tmp_path)
        with pytest.raises(FileNotFoundError):
            svc.get_scene("p1", "e1", "missing")


# ---------------------------------------------------------------------------
# ManifestSchema
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestManifestSchema:
    def test_default_status_is_created(self):
        from app.render.manifest.manifest_schema import SceneAssetManifest
        m = SceneAssetManifest(project_id="p", episode_id="e", scene_id="s")
        assert m.status == "created"

    def test_all_optional_fields_default_empty(self):
        from app.render.manifest.manifest_schema import SceneAssetManifest
        m = SceneAssetManifest(project_id="p", episode_id="e", scene_id="s")
        assert m.word_timings == []
        assert m.detection == {}
        assert m.subtitle_placement == {}
        assert m.drama_metadata == {}
        assert m.provider_payload == {}
        assert m.tts_payload == {}

    def test_error_defaults_to_none(self):
        from app.render.manifest.manifest_schema import SceneAssetManifest
        m = SceneAssetManifest(project_id="p", episode_id="e", scene_id="s")
        assert m.error is None
