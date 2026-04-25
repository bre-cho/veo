from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.render.dependency.dependency_service import DependencyService
from app.render.manifest.manifest_service import ManifestService
from app.render.reassembly._sort_utils import scene_sort_key
from app.render.reassembly.affected_range_resolver import AffectedRangeResolver
from app.render.reassembly.burn_in_mode_resolver import BurnInModeResolver
from app.render.reassembly.chunk_builder import ChunkBuilder
from app.render.reassembly.chunk_index import ChunkIndex
from app.render.reassembly.concat_finalizer import ConcatFinalizer
from app.render.reassembly.per_scene_subtitle_service import PerSceneSubtitleService
from app.render.reassembly.policy.rebuild_policy_engine import RebuildPolicyEngine
from app.render.reassembly.optimizer.rebuild_strategy_optimizer import RebuildStrategyOptimizer
from app.render.reassembly.schemas import SmartReassemblyRequest
from app.render.reassembly.subtitle_rebuild_service import SubtitleRebuildService
from app.render.reassembly.timeline_drift_guard import TimelineDriftGuard
from app.render.reassembly.timeline_rebuilder import TimelineRebuilder


class SmartReassemblyService:
    """Rebuilds only the changed scene chunk and fast-concats the final MP4.

    Typical flow (``force_full_rebuild=False``):

    1. Read the scene manifest to get asset paths.
    2. Detect whether the scene duration has drifted beyond tolerance.
    3. If drift detected: rebuild timeline offsets, rebuild subtitles (mode-aware),
       and rebuild chunks for the changed scene **plus all following scenes**
       (global burn-in) or **only the changed scene** (per-scene burn-in).
    4. Fast-concat all chunks into the final MP4.
    5. Patch affected scene manifests with ``status=smart_reassembled``.

    When ``force_full_rebuild=True``, every scene in the episode is
    re-encoded and a fresh chunk index is written.
    """

    def __init__(
        self,
        manifest_base_dir: str = "/data/renders/manifests",
        chunk_base_dir: str = "/data/renders/chunks",
        dependency_base_dir: str = "/data/renders/dependency",
    ) -> None:
        self._manifest = ManifestService(base_dir=manifest_base_dir)
        self._chunk_index = ChunkIndex(base_dir=chunk_base_dir)
        self._chunk_builder = ChunkBuilder()
        self._finalizer = ConcatFinalizer()
        self._drift_guard = TimelineDriftGuard()
        self._timeline_rebuilder = TimelineRebuilder()
        self._subtitle_rebuilder = SubtitleRebuildService()
        self._affected_range = AffectedRangeResolver(manifest_base_dir=manifest_base_dir)
        self._burn_in_mode = BurnInModeResolver()
        self._per_scene_subtitles = PerSceneSubtitleService(manifest_base_dir=manifest_base_dir)
        self._dependency = DependencyService(
            manifest_base_dir=manifest_base_dir,
            dependency_base_dir=dependency_base_dir,
        )
        self._rebuild_policy = RebuildPolicyEngine()
        self._optimizer = RebuildStrategyOptimizer()

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

            if self._burn_in_mode.mode() == "global_burn_in":
                subtitle_report = self._subtitle_rebuilder.rebuild_episode_subtitles(
                    project_id=req.project_id,
                    episode_id=req.episode_id,
                )
            else:
                subtitle_report = self._per_scene_subtitles.rebuild_scene_subtitle(
                    project_id=req.project_id,
                    episode_id=req.episode_id,
                    scene_id=req.changed_scene_id,
                )

            self._manifest.patch_scene(
                req.project_id,
                req.episode_id,
                req.changed_scene_id,
                {
                    "timeline_drift": drift_report,
                    "timeline_rebuilt": True,
                    "subtitle_rebuilt_after_drift": True,
                    "subtitle_path": subtitle_report.get("subtitle_path") if subtitle_report else None,
                },
            )

        # Determine whether to rebuild only the changed scene or the full
        # affected range (changed scene + all scenes that follow).
        requires_range = self._burn_in_mode.requires_affected_range_rebuild(
            has_timeline_drift=drift_report["has_drift"],
        )

        range_manifests: List[Dict[str, Any]] = self._affected_range.resolve(
            project_id=req.project_id,
            episode_id=req.episode_id,
            changed_scene_id=req.changed_scene_id,
            has_timeline_drift=requires_range,
        )

        # Graph-aware expansion: collect reasons for each affected scene.
        dependency_reasons: Dict[str, Any] = self._dependency.affected_scenes_with_reasons(
            project_id=req.project_id,
            episode_id=req.episode_id,
            changed_scene_id=req.changed_scene_id,
            change_type=req.change_type,
        )

        # Scenes in the affected range due to global subtitle/timeline drift
        # are always required to rebuild; annotate them with a timeline reason.
        if requires_range:
            for item in range_manifests:
                scene_id = item["scene_id"]
                dependency_reasons.setdefault(scene_id, []).append({
                    "source_scene_id": req.changed_scene_id,
                    "dependency_type": "timeline",
                    "reason": "timeline drift requires rebuilding following subtitle-burned chunks",
                    "strength": 1.0,
                })

        # Apply rebuild policy to filter by required / optional / skip.
        policy_decisions = self._rebuild_policy.classify_many(
            reason_report=dependency_reasons,
            force_quality=req.force_quality_rebuild,
        )

        required_ids: set = set(self._rebuild_policy.required_scene_ids(policy_decisions))
        optional_ids: set = set(self._rebuild_policy.optional_scene_ids(policy_decisions))

        if req.include_optional_rebuilds:
            rebuild_ids = required_ids | optional_ids
        else:
            rebuild_ids = required_ids

        # Cost-aware strategy selection.
        all_episode_manifests = self._manifest.list_episode(req.project_id, req.episode_id)
        affected_range_scene_ids = [item["scene_id"] for item in range_manifests]

        optimization = self._optimizer.choose_strategy(
            all_manifests=all_episode_manifests,
            changed_scene_id=req.changed_scene_id,
            required_scene_ids=sorted(required_ids),
            optional_scene_ids=sorted(optional_ids),
            affected_range_scene_ids=affected_range_scene_ids,
            change_type=req.change_type,
            has_timeline_drift=drift_report["has_drift"],
            force_full_rebuild=req.force_full_rebuild,
            include_optional=req.include_optional_rebuilds,
        )

        # Use the optimizer's chosen scene set, but always include any
        # scenes already in rebuild_ids (policy-required or range-mandated).
        optimizer_ids = set(optimization["chosen_strategy"]["scene_ids"])
        rebuild_ids = rebuild_ids | optimizer_ids

        affected_manifests = [
            item
            for item in all_episode_manifests
            if item["scene_id"] in rebuild_ids
        ]
        affected_manifests.sort(key=scene_sort_key)

        rebuilt_chunks: List[Dict[str, Any]] = []

        for item in affected_manifests:
            # Re-read manifest for the changed scene so ChunkBuilder picks up
            # any freshly written subtitle_path from the drift block above.
            fresh_item = self._manifest.get_scene(
                req.project_id,
                req.episode_id,
                item["scene_id"],
            )

            chunk = self._chunk_builder.build_scene_chunk(
                project_id=req.project_id,
                episode_id=req.episode_id,
                scene_manifest=fresh_item,
            )

            rebuilt_chunks.append(chunk)

            order_index = scene_sort_key(item)[0]
            if order_index == 999_999:
                order_index = None  # type: ignore[assignment]
            self._chunk_index.update_chunk(
                project_id=req.project_id,
                episode_id=req.episode_id,
                scene_id=item["scene_id"],
                chunk_path=chunk["chunk_path"],
                duration_sec=chunk["duration_sec"] or 0.0,
                order_index=order_index,
            )

            self._manifest.patch_scene(
                req.project_id,
                req.episode_id,
                item["scene_id"],
                {
                    "status": "smart_reassembled",
                    "chunk_path": chunk["chunk_path"],
                    "needs_reassembly": False,
                    "needs_smart_reassembly": False,
                    "affected_by_timeline_drift": item["scene_id"] != req.changed_scene_id,
                    "rebuild_reasons": dependency_reasons.get(item["scene_id"], []),
                    "rebuild_policy_decision": policy_decisions.get(item["scene_id"]),
                    "rebuild_optimizer_strategy": optimization["chosen_strategy"],
                },
            )

        # Record policy decision for skipped scenes (no rebuild needed).
        for scene_id in self._rebuild_policy.skipped_scene_ids(policy_decisions):
            self._manifest.patch_scene(
                req.project_id,
                req.episode_id,
                scene_id,
                {
                    "rebuild_policy_decision": policy_decisions[scene_id],
                    "needs_reassembly": False,
                },
            )

        # Reload the full index so concat order is always correct.
        index = self._chunk_index.load(req.project_id, req.episode_id)

        final = self._finalizer.concat_chunks(
            project_id=req.project_id,
            episode_id=req.episode_id,
            chunks=index["chunks"],
        )

        self._manifest.patch_scene(
            req.project_id,
            req.episode_id,
            req.changed_scene_id,
            {"final_output_path": final["output_path"]},
        )

        return {
            "status": "smart_reassembled",
            "changed_scene_id": req.changed_scene_id,
            "change_type": req.change_type,
            "timeline_drift": drift_report,
            "timeline_report": timeline_report,
            "subtitle_report": subtitle_report,
            "rebuilt_scene_ids": [c["scene_id"] for c in rebuilt_chunks],
            "rebuild_reason_report": dependency_reasons,
            "rebuild_policy_report": policy_decisions,
            "required_scene_ids": sorted(required_ids),
            "optional_scene_ids": sorted(optional_ids),
            "skipped_scene_ids": self._rebuild_policy.skipped_scene_ids(policy_decisions),
            "rebuild_optimization": optimization,
            "rebuilt_count": len(rebuilt_chunks),
            "final": final,
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

        chunks.sort(key=scene_sort_key)

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

