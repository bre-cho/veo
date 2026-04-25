from __future__ import annotations

from typing import Any, Dict, Optional

from app.render.manifest.manifest_service import ManifestService
from app.render.reassembly.chunk_builder import ChunkBuilder
from app.render.reassembly.chunk_index import ChunkIndex
from app.render.reassembly.concat_finalizer import ConcatFinalizer
from app.render.reassembly.schemas import SmartReassemblyRequest
from app.render.reassembly.subtitle_rebuild_service import SubtitleRebuildService
from app.render.reassembly.timeline_drift_guard import TimelineDriftGuard
from app.render.reassembly.timeline_rebuilder import TimelineRebuilder


class SmartReassemblyService:
    """Rebuilds only the changed scene chunk and fast-concats the final MP4.

    Typical flow (``force_full_rebuild=False``):

    1. Read the scene manifest to get asset paths.
    2. Encode the scene into a single MP4 chunk.
    3. Update the chunk index (replace the old chunk entry).
    4. Fast-concat all chunks into the final MP4.
    5. Patch the scene manifest with ``status=smart_reassembled`` and
       ``needs_reassembly=False``.

    When ``force_full_rebuild=True``, every scene in the episode is
    re-encoded and a fresh chunk index is written.
    """

    def __init__(
        self,
        manifest_base_dir: str = "/data/renders/manifests",
        chunk_base_dir: str = "/data/renders/chunks",
    ) -> None:
        self._manifest = ManifestService(base_dir=manifest_base_dir)
        self._chunk_index = ChunkIndex(base_dir=chunk_base_dir)
        self._chunk_builder = ChunkBuilder()
        self._finalizer = ConcatFinalizer()
        self._drift_guard = TimelineDriftGuard()
        self._timeline_rebuilder = TimelineRebuilder()
        self._subtitle_rebuilder = SubtitleRebuildService()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def reassemble(self, req: SmartReassemblyRequest) -> Dict[str, Any]:
        """Execute the smart reassembly flow described in the class docstring."""
        if req.force_full_rebuild:
            return self._full_rebuild(req)
        return self._smart_rebuild(req)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _smart_rebuild(self, req: SmartReassemblyRequest) -> Dict[str, Any]:
        scene_manifest = self._manifest.get_scene(
            req.project_id,
            req.episode_id,
            req.changed_scene_id,
        )

        drift_report = self._drift_guard.detect_drift(
            old_duration_sec=float(
                scene_manifest.get("previous_duration_sec")
                or scene_manifest.get("duration_sec")
                or 0
            ),
            new_duration_sec=float(scene_manifest.get("duration_sec") or 0),
        )

        timeline_report: Optional[Dict[str, Any]] = None
        subtitle_report: Optional[Dict[str, Any]] = None

        if drift_report["has_drift"]:
            timeline_report = self._timeline_rebuilder.rebuild_episode_offsets(
                project_id=req.project_id,
                episode_id=req.episode_id,
            )

            subtitle_report = self._subtitle_rebuilder.rebuild_episode_subtitles(
                project_id=req.project_id,
                episode_id=req.episode_id,
            )

            self._manifest.patch_scene(
                req.project_id,
                req.episode_id,
                req.changed_scene_id,
                {
                    "timeline_drift": drift_report,
                    "timeline_rebuilt": True,
                    "subtitle_rebuilt_after_drift": True,
                    "subtitle_path": subtitle_report["subtitle_path"],
                },
            )

            # Re-read manifest so chunk builder sees refreshed subtitle_path.
            scene_manifest = self._manifest.get_scene(
                req.project_id,
                req.episode_id,
                req.changed_scene_id,
            )

        chunk = self._chunk_builder.build_scene_chunk(
            project_id=req.project_id,
            episode_id=req.episode_id,
            scene_manifest=scene_manifest,
        )

        index = self._chunk_index.update_chunk(
            project_id=req.project_id,
            episode_id=req.episode_id,
            scene_id=req.changed_scene_id,
            chunk_path=chunk["chunk_path"],
            duration_sec=chunk["duration_sec"] or 0.0,
        )

        final = self._finalizer.concat_chunks(
            project_id=req.project_id,
            episode_id=req.episode_id,
            chunks=index["chunks"],
        )

        self._manifest.patch_scene(
            req.project_id,
            req.episode_id,
            req.changed_scene_id,
            {
                "status": "smart_reassembled",
                "chunk_path": chunk["chunk_path"],
                "final_output_path": final["output_path"],
                "needs_reassembly": False,
                "needs_smart_reassembly": False,
            },
        )

        return {
            "status": "smart_reassembled",
            "rebuilt_scene_id": req.changed_scene_id,
            "chunk": chunk,
            "final": final,
            "timeline_drift": drift_report,
            "timeline_report": timeline_report,
            "subtitle_report": subtitle_report,
        }

    def _full_rebuild(self, req: SmartReassemblyRequest) -> Dict[str, Any]:
        manifests = self._manifest.list_episode(req.project_id, req.episode_id)

        chunks = []
        for scene_manifest in manifests:
            chunk = self._chunk_builder.build_scene_chunk(
                project_id=req.project_id,
                episode_id=req.episode_id,
                scene_manifest=scene_manifest,
            )
            chunks.append(chunk)

        chunks.sort(key=lambda c: c["scene_id"])

        index: Dict[str, Any] = {
            "project_id": req.project_id,
            "episode_id": req.episode_id,
            "chunks": chunks,
        }
        self._chunk_index.save(req.project_id, req.episode_id, index)

        final = self._finalizer.concat_chunks(
            project_id=req.project_id,
            episode_id=req.episode_id,
            chunks=chunks,
        )

        return {
            "status": "full_reassembled",
            "chunks": chunks,
            "final": final,
        }
