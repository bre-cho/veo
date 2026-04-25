"""factory_render_adapter – builds a fully-populated render manifest and
RenderJob record from FactoryContext pipeline outputs.

The adapter bridges the factory pipeline (which accumulates scenes, audio,
avatar, subtitle) and the render execution layer (which expects a structured
RenderJob + RenderSceneTask rows + a manifest payload).
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Deterministic render-job UUID namespace (same as factory_orchestrator)
_FACTORY_RENDER_NS = uuid.UUID("6ba7b812-9dad-11d1-80b4-00c04fd430ca")


class FactoryRenderAdapter:
    """Constructs a fully-populated RenderJob + scene tasks from FactoryContext.

    Usage::

        adapter = FactoryRenderAdapter()
        manifest = adapter.build_and_persist(ctx, db)
    """

    def build_manifest(
        self,
        run_id: str,
        project_id: str | None,
        scenes: list[dict[str, Any]],
        avatar_id: str | None,
        audio_url: str | None,
        render_plan: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Build a render manifest dict from factory context fields.

        Returns a serialisable dict that can be stored in
        ``RenderJob.final_timeline`` / passed to the dispatch task.
        """
        plan = render_plan or {}
        scene_entries = []
        for scene in scenes:
            scene_entry: dict[str, Any] = {
                "scene_index": scene.get("scene_index", 0),
                "title": scene.get("visual_prompt") or f"Scene {scene.get('scene_index', 0) + 1}",
                "voiceover": scene.get("voiceover", ""),
                "subtitle_text": scene.get("subtitle_text", ""),
                "avatar_instruction": scene.get("avatar_instruction") or f"avatar_id={avatar_id or 'default_avatar'}",
                "camera_instruction": scene.get("camera_instruction", "medium_shot"),
                "duration": scene.get("duration", 5.0),
                "visual_type": scene.get("visual_type", "avatar"),
                "status": "queued",
            }
            if audio_url:
                scene_entry["audio_url"] = audio_url
            scene_entries.append(scene_entry)

        manifest: dict[str, Any] = {
            "format_version": "1.0",
            "run_id": run_id,
            "project_id": project_id,
            "avatar_id": avatar_id or "default_avatar",
            "audio_url": audio_url,
            "provider": plan.get("provider", "auto"),
            "strategy": plan.get("selected_strategy", "full_rebuild"),
            "scene_count": len(scenes),
            "scenes": scene_entries,
            "estimated_duration_seconds": sum(s.get("duration", 5.0) for s in scenes),
            "estimated_cost": plan.get("estimated_cost", {}),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Subtitle manifest entry: per-scene subtitle segments derived from scenes
        subtitle_segments = [
            {
                "scene_index": s.get("scene_index", i),
                "text": s.get("subtitle_text") or s.get("voiceover", ""),
                "start_ms": int(sum(sc.get("duration", 5.0) for sc in scenes[:i]) * 1000),
                "duration_ms": int(s.get("duration", 5.0) * 1000),
            }
            for i, s in enumerate(scenes)
        ]
        manifest["subtitle_segments"] = subtitle_segments

        return manifest

    def build_and_persist(
        self,
        run_id: str,
        project_id: str | None,
        render_job_id: str,
        scenes: list[dict[str, Any]],
        avatar_id: str | None,
        audio_url: str | None,
        render_plan: dict[str, Any] | None,
        db: Session,
    ) -> dict[str, Any]:
        """Build manifest and upsert RenderJob + RenderSceneTask rows.

        Returns the manifest dict.  Never raises — all DB errors are caught
        and logged so that a failure here does not abort the pipeline.
        """
        manifest = self.build_manifest(
            run_id=run_id,
            project_id=project_id,
            scenes=scenes,
            avatar_id=avatar_id,
            audio_url=audio_url,
            render_plan=render_plan,
        )

        if project_id is None:
            logger.info(
                "FactoryRenderAdapter: no project_id, manifest built but not persisted (run_id=%s)",
                run_id,
            )
            return manifest

        try:
            from app.models.render_job import RenderJob
            from app.models.render_scene_task import RenderSceneTask

            # Upsert RenderJob
            job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
            if job is None:
                job = RenderJob(
                    id=render_job_id,
                    project_id=project_id,
                    provider=manifest.get("provider", "auto"),
                    status="queued",
                )
                db.add(job)

            # Populate full fields
            job.planned_scene_count = len(scenes)
            job.final_timeline = manifest
            job.final_timeline_json = json.dumps(manifest)
            job.subtitle_segments = manifest.get("subtitle_segments")
            db.flush()

            # Upsert scene tasks
            for scene_entry in manifest["scenes"]:
                task_id = str(uuid.uuid5(
                    _FACTORY_RENDER_NS,
                    f"{render_job_id}:scene:{scene_entry['scene_index']}",
                ))
                existing_task = (
                    db.query(RenderSceneTask)
                    .filter(RenderSceneTask.id == task_id)
                    .first()
                )
                if existing_task is None:
                    task = RenderSceneTask(
                        id=task_id,
                        job_id=render_job_id,
                        scene_index=scene_entry["scene_index"],
                        title=scene_entry["title"],
                        provider=manifest.get("provider", "auto"),
                        status="queued",
                        request_payload_json=json.dumps(scene_entry),
                    )
                    db.add(task)

            db.commit()
            logger.info(
                "FactoryRenderAdapter: persisted render_job=%s with %d scenes (run_id=%s)",
                render_job_id, len(scenes), run_id,
            )

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "FactoryRenderAdapter: DB persist failed (%s), manifest still returned (run_id=%s)",
                exc, run_id,
            )
            try:
                db.rollback()
            except Exception:
                pass

        return manifest
