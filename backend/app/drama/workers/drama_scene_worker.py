from __future__ import annotations

from uuid import UUID

from celery import shared_task
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.drama.models.scene_drama_state import DramaSceneState
from app.drama.services.arc_service import DramaArcService
from app.drama.services.memory_service import DramaMemoryService
from app.drama.services.scene_drama_service import SceneDramaService
from app.drama.services.drama_compiler_service import DramaCompilerService


def _to_uuid(value) -> UUID | None:
    return UUID(str(value)) if value else None


@shared_task(name="app.drama.workers.process_scene")
def process_scene(scene_id: str, scene_context: dict) -> dict:
    """Phase 4 orchestration worker.

    Flow:
    1. Analyze scene drama.
    2. Compile render bridge payload.
    3. Persist scene state.
    4. Persist memory traces.
    5. Increment arc state.

    NOTE: exact Celery wiring / retry policy should be adapted to the target repo.
    """
    db: Session = SessionLocal()
    try:
        project_id = UUID(str(scene_context["project_id"]))
        scene_uuid = UUID(str(scene_context["scene_id"]))
        character_ids = [UUID(str(x)) for x in (scene_context.get("character_ids") or [c["character_id"] for c in scene_context.get("characters", [])])]

        analysis_service = SceneDramaService(db)
        compiler_service = DramaCompilerService()
        memory_service = DramaMemoryService(db)
        arc_service = DramaArcService(db)

        analysis = analysis_service.analyze_scene(
            project_id=project_id,
            scene_id=scene_uuid,
            character_ids=character_ids,
            scene_context=scene_context,
        )
        compile_payload = compiler_service.compile_scene_payload(analysis)

        scene_state = db.query(DramaSceneState).filter(DramaSceneState.scene_id == scene_uuid).one_or_none()
        if scene_state is None:
            scene_state = DramaSceneState(
                scene_id=scene_uuid,
                project_id=project_id,
                episode_id=UUID(str(scene_context["episode_id"])) if scene_context.get("episode_id") else None,
            )
            db.add(scene_state)

        drama_state = analysis.get("drama_state", {})
        scene_state.project_id = project_id
        scene_state.episode_id = UUID(str(scene_context["episode_id"])) if scene_context.get("episode_id") else None
        scene_state.scene_goal = scene_context.get("scene_goal")
        scene_state.visible_conflict = scene_context.get("visible_conflict")
        scene_state.hidden_conflict = scene_context.get("hidden_conflict")
        scene_state.scene_temperature = float(drama_state.get("tension_score", 0.0))
        scene_state.pressure_level = float(drama_state.get("pressure_level", 0.0))
        scene_state.dominant_character_id = _to_uuid(drama_state.get("dominant_character_id"))
        scene_state.emotional_center_character_id = _to_uuid(drama_state.get("emotional_center_character_id"))
        scene_state.threatened_character_id = _to_uuid(drama_state.get("threatened_character_id"))
        scene_state.turning_point = drama_state.get("turning_point")
        scene_state.outcome_type = drama_state.get("outcome_type")
        scene_state.power_shift_delta = float(drama_state.get("power_shift_delta", 0.0))
        scene_state.trust_shift_delta = float(drama_state.get("trust_shift_delta", 0.0))
        scene_state.exposure_shift_delta = float(drama_state.get("exposure_shift_delta", 0.0))
        scene_state.dependency_shift_delta = float(drama_state.get("dependency_shift_delta", 0.0))
        scene_state.analysis_payload = analysis
        scene_state.compile_payload = compile_payload
        db.flush()

        memory_payloads = memory_service.build_scene_memory_payloads(scene_uuid, analysis)
        if memory_payloads:
            memory_service.bulk_create_traces(memory_payloads)

        arc_character_ids = scene_context.get("character_ids") or [
            c["character_id"] for c in scene_context.get("characters", [])
        ]
        for raw_id in arc_character_ids:
            character_id = UUID(str(raw_id))
            current_arc = arc_service.get_latest_arc(
                character_id=character_id,
                episode_id=_to_uuid(analysis.get("episode_id")),
            )
            arc_payload = arc_service.build_arc_payload(
                character_id=character_id,
                analysis=analysis,
                current_arc=current_arc,
            )
            arc_service.create_or_update_arc(arc_payload)

        db.commit()
        return {
            "ok": True,
            "scene_id": scene_id,
            "analysis": analysis,
            "compile_payload": compile_payload,
            "memory_traces_created": len(memory_payloads),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
