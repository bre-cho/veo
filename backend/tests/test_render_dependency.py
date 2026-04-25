"""Tests for the Scene Dependency Graph module.

All filesystem I/O is redirected to temporary directories so tests are
self-contained and leave no artefacts behind.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

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


# ===========================================================================
# DependencyGraph
# ===========================================================================

from app.render.dependency.dependency_graph import DependencyGraph  # noqa: E402


class TestDependencyGraph:
    def _timeline_dep(self, src: str, tgt: str) -> Dict[str, Any]:
        return {
            "source_scene_id": src,
            "target_scene_id": tgt,
            "dependency_type": "timeline",
            "reason": "later depends on earlier",
            "strength": 1.0,
        }

    def _dep(self, src: str, tgt: str, dep_type: str) -> Dict[str, Any]:
        return {
            "source_scene_id": src,
            "target_scene_id": tgt,
            "dependency_type": dep_type,
            "reason": f"test {dep_type}",
            "strength": 0.8,
        }

    def test_include_self_default(self):
        g = DependencyGraph([])
        result = g.affected_scenes("s1", "subtitle")
        assert "s1" in result

    def test_exclude_self(self):
        g = DependencyGraph([])
        result = g.affected_scenes("s1", "subtitle", include_self=False)
        assert result == []

    def test_direct_timeline_dep(self):
        deps = [self._timeline_dep("s1", "s2"), self._timeline_dep("s1", "s3")]
        g = DependencyGraph(deps)
        result = g.affected_scenes("s1", "timeline")
        assert set(result) == {"s1", "s2", "s3"}

    def test_transitive_timeline_dep(self):
        deps = [self._timeline_dep("s1", "s2"), self._timeline_dep("s2", "s3")]
        g = DependencyGraph(deps)
        result = g.affected_scenes("s1", "timeline")
        assert set(result) == {"s1", "s2", "s3"}

    def test_change_type_subtitle_only_matches_subtitle(self):
        deps = [
            self._dep("s1", "s2", "subtitle"),
            self._dep("s1", "s3", "avatar"),
        ]
        g = DependencyGraph(deps)
        result = g.affected_scenes("s1", "subtitle")
        # subtitle dep matched; avatar dep not matched
        assert "s2" in result
        assert "s3" not in result

    def test_voice_change_matches_subtitle_and_timeline(self):
        deps = [
            self._dep("s1", "s2", "subtitle"),
            self._dep("s1", "s3", "timeline"),
            self._dep("s1", "s4", "avatar"),
        ]
        g = DependencyGraph(deps)
        result = g.affected_scenes("s1", "voice")
        assert "s2" in result  # subtitle pulled in by voice
        assert "s3" in result  # timeline pulled in by voice
        assert "s4" not in result  # avatar not pulled in by voice

    def test_avatar_change_matches_continuity_and_style(self):
        deps = [
            self._dep("s1", "s2", "continuity"),
            self._dep("s1", "s3", "style"),
            self._dep("s1", "s4", "timeline"),
        ]
        g = DependencyGraph(deps)
        result = g.affected_scenes("s1", "avatar")
        assert "s2" in result
        assert "s3" in result
        assert "s4" not in result

    def test_change_type_all_matches_everything(self):
        deps = [
            self._dep("s1", "s2", "subtitle"),
            self._dep("s1", "s3", "avatar"),
            self._dep("s1", "s4", "timeline"),
        ]
        g = DependencyGraph(deps)
        result = g.affected_scenes("s1", "all")
        assert set(result) == {"s1", "s2", "s3", "s4"}

    def test_no_matching_deps_returns_only_self(self):
        deps = [self._dep("s2", "s3", "subtitle")]
        g = DependencyGraph(deps)
        result = g.affected_scenes("s1", "subtitle")
        assert result == ["s1"]

    def test_cycles_do_not_loop_forever(self):
        # Mutual dependency: s1 → s2 → s1
        deps = [
            self._dep("s1", "s2", "avatar"),
            self._dep("s2", "s1", "avatar"),
        ]
        g = DependencyGraph(deps)
        result = g.affected_scenes("s1", "avatar")
        assert set(result) == {"s1", "s2"}


# ===========================================================================
# DependencyResolver
# ===========================================================================

from app.render.dependency.dependency_resolver import DependencyResolver  # noqa: E402


class TestDependencyResolver:
    def _manifest(self, scene_id: str, order_index: int, **kwargs) -> Dict[str, Any]:
        return {"scene_id": scene_id, "order_index": order_index, **kwargs}

    def test_empty_manifests_returns_no_deps(self):
        r = DependencyResolver()
        assert r.build_from_manifests([]) == []

    def test_single_scene_returns_no_deps(self):
        r = DependencyResolver()
        deps = r.build_from_manifests([self._manifest("s1", 0)])
        assert deps == []

    def test_timeline_deps_created_for_later_scenes(self):
        r = DependencyResolver()
        manifests = [
            self._manifest("s1", 0),
            self._manifest("s2", 1),
            self._manifest("s3", 2),
        ]
        deps = r.build_from_manifests(manifests)
        timeline_deps = [d for d in deps if d["dependency_type"] == "timeline"]
        # s1→s2, s1→s3, s2→s3
        pairs = {(d["source_scene_id"], d["target_scene_id"]) for d in timeline_deps}
        assert ("s1", "s2") in pairs
        assert ("s1", "s3") in pairs
        assert ("s2", "s3") in pairs
        # Earlier scenes are NOT impacted by later scenes
        assert ("s2", "s1") not in pairs
        assert ("s3", "s1") not in pairs

    def test_avatar_deps_created_for_shared_avatar(self):
        r = DependencyResolver()
        manifests = [
            self._manifest("s1", 0, avatar_id="av1"),
            self._manifest("s2", 1, avatar_id="av1"),
            self._manifest("s3", 2, avatar_id="av2"),
        ]
        deps = r.build_from_manifests(manifests)
        avatar_pairs = {
            (d["source_scene_id"], d["target_scene_id"])
            for d in deps if d["dependency_type"] == "avatar"
        }
        assert ("s1", "s2") in avatar_pairs
        assert ("s2", "s1") in avatar_pairs
        assert ("s1", "s3") not in avatar_pairs

    def test_style_deps_created_for_shared_style(self):
        r = DependencyResolver()
        manifests = [
            self._manifest("s1", 0, style_id="sty1"),
            self._manifest("s2", 1, style_id="sty1"),
        ]
        deps = r.build_from_manifests(manifests)
        style_pairs = {
            (d["source_scene_id"], d["target_scene_id"])
            for d in deps if d["dependency_type"] == "style"
        }
        assert ("s1", "s2") in style_pairs
        assert ("s2", "s1") in style_pairs

    def test_shared_asset_deps_created_on_overlap(self):
        r = DependencyResolver()
        manifests = [
            self._manifest("s1", 0, shared_assets=["bg1", "music1"]),
            self._manifest("s2", 1, shared_assets=["music1"]),
            self._manifest("s3", 2, shared_assets=["bg2"]),
        ]
        deps = r.build_from_manifests(manifests)
        asset_pairs = {
            (d["source_scene_id"], d["target_scene_id"])
            for d in deps if d["dependency_type"] == "shared_asset"
        }
        assert ("s1", "s2") in asset_pairs  # music1 overlap
        assert ("s1", "s3") not in asset_pairs  # no overlap

    def test_order_index_sort_determines_timeline_direction(self):
        r = DependencyResolver()
        # scene_10 has order_index=9, scene_2 has order_index=1
        manifests = [
            self._manifest("scene_10", 9),
            self._manifest("scene_1", 0),
            self._manifest("scene_2", 1),
        ]
        deps = r.build_from_manifests(manifests)
        timeline_pairs = [
            (d["source_scene_id"], d["target_scene_id"])
            for d in deps if d["dependency_type"] == "timeline"
        ]
        # scene_1 (idx 0) → scene_2 (idx 1) and scene_10 (idx 2)
        assert ("scene_1", "scene_2") in timeline_pairs
        assert ("scene_1", "scene_10") in timeline_pairs
        # scene_2 (idx 1) → scene_10 (idx 2) only
        assert ("scene_2", "scene_10") in timeline_pairs
        # scene_10 must NOT create timeline deps to earlier scenes
        assert ("scene_10", "scene_1") not in timeline_pairs
        assert ("scene_10", "scene_2") not in timeline_pairs


# ===========================================================================
# DependencyService
# ===========================================================================

from app.render.dependency.dependency_service import DependencyService  # noqa: E402


class TestDependencyService:
    def _svc(self, tmp_path: Path) -> DependencyService:
        return DependencyService(
            manifest_base_dir=str(tmp_path / "manifests"),
            dependency_base_dir=str(tmp_path / "dependency"),
        )

    def _write(self, tmp_path: Path, scene_id: str, order_index: int, **extra) -> None:
        _write_manifest(
            str(tmp_path / "manifests"),
            "p1",
            "ep1",
            scene_id,
            {"order_index": order_index, **extra},
        )

    def test_build_graph_returns_dict_with_keys(self, tmp_path):
        self._write(tmp_path, "s1", 0)
        self._write(tmp_path, "s2", 1)
        svc = self._svc(tmp_path)
        graph = svc.build_graph("p1", "ep1")
        assert graph["project_id"] == "p1"
        assert graph["episode_id"] == "ep1"
        assert "dependencies" in graph
        assert "scene_metadata" in graph

    def test_build_graph_persists_file(self, tmp_path):
        self._write(tmp_path, "s1", 0)
        svc = self._svc(tmp_path)
        svc.build_graph("p1", "ep1")
        path = svc.graph_path("p1", "ep1")
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["project_id"] == "p1"

    def test_load_graph_builds_when_missing(self, tmp_path):
        self._write(tmp_path, "s1", 0)
        svc = self._svc(tmp_path)
        # Don't call build_graph first
        graph = svc.load_graph("p1", "ep1")
        assert "dependencies" in graph

    def test_load_graph_reads_existing_file(self, tmp_path):
        self._write(tmp_path, "s1", 0)
        self._write(tmp_path, "s2", 1)
        svc = self._svc(tmp_path)
        svc.build_graph("p1", "ep1")
        # Tamper with file to confirm load reads persisted version
        path = svc.graph_path("p1", "ep1")
        data = json.loads(path.read_text())
        data["_tamper"] = True
        path.write_text(json.dumps(data))
        loaded = svc.load_graph("p1", "ep1")
        assert loaded.get("_tamper") is True

    def test_affected_scenes_subtitle_returns_only_self(self, tmp_path):
        """A subtitle-only change on a scene with no subtitle deps → just itself."""
        self._write(tmp_path, "s1", 0)
        self._write(tmp_path, "s2", 1)
        self._write(tmp_path, "s3", 2)
        svc = self._svc(tmp_path)
        svc.build_graph("p1", "ep1")
        result = svc.affected_scenes("p1", "ep1", "s1", "subtitle")
        # s1 is in result; s2/s3 are not because there are no subtitle edges
        # (resolver only creates timeline edges for basic scenes)
        assert "s1" in result
        assert "s2" not in result

    def test_affected_scenes_voice_includes_timeline(self, tmp_path):
        """A voice change on s1 should pull in s2/s3 via timeline edges."""
        self._write(tmp_path, "s1", 0)
        self._write(tmp_path, "s2", 1)
        self._write(tmp_path, "s3", 2)
        svc = self._svc(tmp_path)
        svc.build_graph("p1", "ep1")
        result = svc.affected_scenes("p1", "ep1", "s1", "voice")
        # voice → timeline edges → s2, s3 affected
        assert "s1" in result
        assert "s2" in result
        assert "s3" in result

    def test_affected_scenes_avatar_includes_shared_avatar(self, tmp_path):
        self._write(tmp_path, "s1", 0, avatar_id="av1")
        self._write(tmp_path, "s2", 1)
        self._write(tmp_path, "s3", 2, avatar_id="av1")
        svc = self._svc(tmp_path)
        svc.build_graph("p1", "ep1")
        result = svc.affected_scenes("p1", "ep1", "s1", "avatar")
        assert "s1" in result
        assert "s3" in result
        assert "s2" not in result  # s2 has no avatar dep

    def test_scene_metadata_populated(self, tmp_path):
        self._write(tmp_path, "s1", 0, avatar_id="av1", style_id="sty1")
        svc = self._svc(tmp_path)
        graph = svc.build_graph("p1", "ep1")
        meta = graph["scene_metadata"]["s1"]
        assert meta["avatar_id"] == "av1"
        assert meta["style_id"] == "sty1"
        assert meta["order_index"] == 0


# ===========================================================================
# SmartReassemblyRequest — change_type field
# ===========================================================================

from app.render.reassembly.schemas import SmartReassemblyRequest  # noqa: E402


class TestSmartReassemblyRequestChangeType:
    def test_default_change_type_is_subtitle(self):
        req = SmartReassemblyRequest(
            project_id="p", episode_id="e", changed_scene_id="s1"
        )
        assert req.change_type == "subtitle"

    def test_change_type_can_be_set(self):
        req = SmartReassemblyRequest(
            project_id="p", episode_id="e", changed_scene_id="s1", change_type="voice"
        )
        assert req.change_type == "voice"


# ===========================================================================
# SmartReassemblyService — dependency integration
# ===========================================================================

from app.render.reassembly.smart_reassembly_service import SmartReassemblyService  # noqa: E402


class TestSmartReassemblyDependencyIntegration:
    """Verify that SmartReassemblyService expands affected scenes via the
    dependency graph when change_type implies a wider rebuild."""

    def _write(self, base_dir: str, scene_id: str, order_index: int, **extra) -> None:
        _write_manifest(base_dir, "p1", "ep1", scene_id, {
            "order_index": order_index,
            "video_path": f"/v/{scene_id}.mp4",
            "audio_path": f"/a/{scene_id}.wav",
            "duration_sec": 5.0,
            **extra,
        })

    def test_avatar_change_type_rebuilds_shared_avatar_scenes(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        chunks_dir = str(tmp_path / "chunks")
        dep_dir = str(tmp_path / "dependency")

        self._write(manifests_dir, "s1", 0, avatar_id="av1")
        self._write(manifests_dir, "s2", 1)
        self._write(manifests_dir, "s3", 2, avatar_id="av1")

        svc = SmartReassemblyService(
            manifest_base_dir=manifests_dir,
            chunk_base_dir=chunks_dir,
            dependency_base_dir=dep_dir,
        )

        # Pre-build the dependency graph so the service can load it
        svc._dependency.build_graph("p1", "ep1")

        mock_chunk_fn = lambda project_id, episode_id, scene_manifest: {
            "scene_id": scene_manifest["scene_id"],
            "order_index": scene_manifest.get("order_index"),
            "chunk_path": f"/chunks/{scene_manifest['scene_id']}.mp4",
            "duration_sec": 5.0,
        }
        mock_final = {"status": "succeeded", "output_path": "/final/ep1.mp4"}

        from app.render.reassembly.schemas import SmartReassemblyRequest

        req = SmartReassemblyRequest(
            project_id="p1",
            episode_id="ep1",
            changed_scene_id="s1",
            change_type="avatar",
        )

        with patch.object(svc._chunk_builder, "build_scene_chunk", side_effect=mock_chunk_fn), \
             patch.object(svc._finalizer, "concat_chunks", return_value=mock_final):
            result = svc.reassemble(req)

        # s1 (changed) and s3 (shares avatar_id) must be rebuilt
        rebuilt = set(result["rebuilt_scene_ids"])
        assert "s1" in rebuilt
        assert "s3" in rebuilt
        # s2 has no avatar dep so it must NOT be rebuilt
        assert "s2" not in rebuilt

    def test_subtitle_change_type_rebuilds_only_changed_scene(self, tmp_path):
        manifests_dir = str(tmp_path / "manifests")
        chunks_dir = str(tmp_path / "chunks")
        dep_dir = str(tmp_path / "dependency")

        self._write(manifests_dir, "s1", 0)
        self._write(manifests_dir, "s2", 1)
        self._write(manifests_dir, "s3", 2)

        svc = SmartReassemblyService(
            manifest_base_dir=manifests_dir,
            chunk_base_dir=chunks_dir,
            dependency_base_dir=dep_dir,
        )

        svc._dependency.build_graph("p1", "ep1")

        mock_chunk_fn = lambda project_id, episode_id, scene_manifest: {
            "scene_id": scene_manifest["scene_id"],
            "order_index": scene_manifest.get("order_index"),
            "chunk_path": f"/chunks/{scene_manifest['scene_id']}.mp4",
            "duration_sec": 5.0,
        }
        mock_final = {"status": "succeeded", "output_path": "/final/ep1.mp4"}

        from app.render.reassembly.schemas import SmartReassemblyRequest

        req = SmartReassemblyRequest(
            project_id="p1",
            episode_id="ep1",
            changed_scene_id="s2",
            change_type="subtitle",
        )

        with patch.object(svc._chunk_builder, "build_scene_chunk", side_effect=mock_chunk_fn), \
             patch.object(svc._finalizer, "concat_chunks", return_value=mock_final):
            result = svc.reassemble(req)

        rebuilt = set(result["rebuilt_scene_ids"])
        assert "s2" in rebuilt
        # subtitle change does not pull in unrelated scenes
        assert "s1" not in rebuilt
        assert "s3" not in rebuilt
