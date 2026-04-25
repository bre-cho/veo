from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.drama.models.drama_blocking_plan import DramaBlockingPlan
from app.drama.models.drama_camera_plan import DramaCameraPlan
from app.drama.models.drama_dialogue_subtext import DramaDialogueSubtext
from app.drama.models.drama_power_shift import DramaPowerShift
from app.drama.models.scene_drama_state import DramaSceneState
from app.drama.schemas.blocking import BlockingPlanRead
from app.drama.schemas.camera_plan import CameraPlanRead
from app.drama.schemas.dialogue_subtext import DialogueSubtextRead
from app.drama.schemas.power_shift import PowerShiftRead
from app.drama.schemas.drama_state import SceneDramaStateRead
from app.drama.schemas.scene_drama import (
    AnalyzeSceneRequest,
    ApplySceneOutcomeRequest,
    CompileSceneRequest,
    SceneDramaAnalyzeRequest,
    SceneDramaAnalyzeResponse,
)
from app.drama.services.continuity_service import ContinuityService
from app.drama.services.scene_drama_service import SceneDramaService
from app.drama.services.drama_compiler_service import DramaCompilerService

router = APIRouter(prefix="/api/v1/drama/scenes", tags=["drama_scenes"])


def _to_uuid(value) -> UUID | None:
    return UUID(str(value)) if value else None


@router.post("/analyze", response_model=SceneDramaAnalyzeResponse)
def analyze_scene(
    payload: SceneDramaAnalyzeRequest,
    db: Session = Depends(get_db),
) -> SceneDramaAnalyzeResponse:
    result = SceneDramaService(db).analyze_scene(
        project_id=payload.project_id,
        scene_id=payload.scene_id,
        character_ids=payload.character_ids,
        scene_context=payload.scene_context,
    )
    return SceneDramaAnalyzeResponse(**result)


@router.post("/{scene_id}/analyze", response_model=SceneDramaAnalyzeResponse)
def analyze_scene_by_id(
    scene_id: UUID,
    payload: AnalyzeSceneRequest,
    db: Session = Depends(get_db),
) -> SceneDramaAnalyzeResponse:
    result = SceneDramaService(db).analyze_scene(
        project_id=payload.project_id,
        scene_id=scene_id,
        character_ids=payload.character_ids,
        scene_context=payload.scene_context,
    )

    state = db.query(DramaSceneState).filter(DramaSceneState.scene_id == scene_id).first()
    if state is None:
        state = DramaSceneState(
            scene_id=scene_id,
            project_id=payload.project_id,
            episode_id=_to_uuid((payload.scene_context or {}).get("episode_id")),
        )
        db.add(state)
    state.analysis_payload = result

    drama_state = result.get("drama_state", {})
    state.scene_goal = (payload.scene_context or {}).get("scene_goal")
    state.visible_conflict = (payload.scene_context or {}).get("visible_conflict")
    state.hidden_conflict = (payload.scene_context or {}).get("hidden_conflict")
    state.scene_temperature = float(drama_state.get("tension_score", 0.0))
    state.pressure_level = float(drama_state.get("pressure_level", 0.0))
    state.dominant_character_id = _to_uuid(drama_state.get("dominant_character_id"))
    state.threatened_character_id = _to_uuid(drama_state.get("threatened_character_id"))
    state.emotional_center_character_id = _to_uuid(drama_state.get("emotional_center_character_id"))
    state.turning_point = drama_state.get("turning_point")
    state.outcome_type = drama_state.get("outcome_type")
    state.power_shift_delta = float(drama_state.get("power_shift_delta", 0.0))
    state.trust_shift_delta = float(drama_state.get("trust_shift_delta", 0.0))
    state.exposure_shift_delta = float(drama_state.get("exposure_shift_delta", 0.0))
    state.dependency_shift_delta = float(drama_state.get("dependency_shift_delta", 0.0))

    db.commit()

    return SceneDramaAnalyzeResponse(**result)


@router.post("/{scene_id}/compile")
def compile_scene(
    scene_id: UUID,
    payload: CompileSceneRequest,
    db: Session = Depends(get_db),
) -> dict:
    scene_state = db.query(DramaSceneState).filter(DramaSceneState.scene_id == scene_id).first()
    if scene_state is None:
        scene_state = DramaSceneState(scene_id=scene_id, project_id=payload.project_id, episode_id=payload.episode_id)
        db.add(scene_state)

    effective_analysis = payload.scene_analysis or (scene_state.analysis_payload or {})

    compiled = DramaCompilerService().compile_scene(
        scene_context={"scene_id": str(scene_id), **(payload.scene_context or {})},
        scene_analysis=effective_analysis,
        previous_scene_state=payload.previous_scene_state,
        character_arc_state=payload.character_arc_state,
    )

    scene_state.compile_payload = compiled
    db.add(scene_state)

    blocking_plan = compiled.get("blocking_plan") or {}
    camera_plan = compiled.get("camera_plan") or {}

    blocking_row = db.query(DramaBlockingPlan).filter(DramaBlockingPlan.scene_id == scene_id).first()
    if blocking_row is None:
        blocking_row = DramaBlockingPlan(scene_id=scene_id, project_id=payload.project_id, episode_id=payload.episode_id)
    blocking_row.spatial_mode = blocking_plan.get("spatial_mode")
    blocking_row.payload = blocking_plan
    blocking_row.notes = "\n".join(blocking_plan.get("blocking_notes", [])) if blocking_plan.get("blocking_notes") else None
    db.add(blocking_row)

    camera_row = db.query(DramaCameraPlan).filter(DramaCameraPlan.scene_id == scene_id).first()
    if camera_row is None:
        camera_row = DramaCameraPlan(scene_id=scene_id, project_id=payload.project_id, episode_id=payload.episode_id)
    camera_row.primary_shot = camera_plan.get("primary_shot")
    camera_row.primary_move = camera_plan.get("primary_move")
    camera_row.lens_psychology_mode = camera_plan.get("lens_psychology_mode")
    camera_row.reveal_timing = camera_plan.get("reveal_timing")
    camera_row.movement_strategy = camera_plan.get("movement_strategy")
    camera_row.render_bridge_tokens = camera_plan.get("render_bridge_tokens")
    camera_row.payload = camera_plan
    camera_row.notes = "\n".join(camera_plan.get("camera_notes", [])) if camera_plan.get("camera_notes") else None
    db.add(camera_row)

    subtext_map = effective_analysis.get("subtext_map", [])
    if subtext_map:
        db.query(DramaDialogueSubtext).filter(DramaDialogueSubtext.scene_id == scene_id).delete()
        for idx, item in enumerate(subtext_map):
            db.add(
                DramaDialogueSubtext(
                    project_id=payload.project_id,
                    episode_id=payload.episode_id,
                    scene_id=scene_id,
                    line_index=idx,
                    speaker_id=_to_uuid(item.get("speaker_id")),
                    target_id=_to_uuid(item.get("target_id")),
                    literal_intent=item.get("literal_intent") or item.get("psychological_action"),
                    hidden_intent=item.get("hidden_intent"),
                    psychological_action=item.get("psychological_action"),
                    suggested_subtext=item.get("suggested_subtext"),
                    threat_level=float(item.get("threat_level", 0.0) or 0.0),
                )
            )

    power_shift = effective_analysis.get("power_shift") or {}
    if power_shift:
        dominant_id = (
            power_shift.get("from_character_id")
            or power_shift.get("dominant_character_id")
            or effective_analysis.get("dominant_character_id")
        )
        target_id = (
            power_shift.get("to_character_id")
            or power_shift.get("threatened_character_id")
            or effective_analysis.get("threatened_character_id")
        )
        if dominant_id and target_id:
            db.query(DramaPowerShift).filter(DramaPowerShift.scene_id == scene_id).delete()
            db.add(
                DramaPowerShift(
                    project_id=payload.project_id,
                    episode_id=payload.episode_id,
                    scene_id=scene_id,
                    from_character_id=_to_uuid(dominant_id),
                    to_character_id=_to_uuid(target_id),
                    trigger_event=power_shift.get("trigger_event"),
                    social_delta=float(power_shift.get("social_delta", 0.0) or 0.0),
                    emotional_delta=float(power_shift.get("emotional_delta", 0.0) or 0.0),
                    informational_delta=float(power_shift.get("informational_delta", 0.0) or 0.0),
                    moral_delta=float(power_shift.get("moral_delta", 0.0) or 0.0),
                    spatial_delta=float(power_shift.get("spatial_delta", 0.0) or 0.0),
                    narrative_control_delta=float(power_shift.get("narrative_control_delta", 0.0) or 0.0),
                )
            )

    db.commit()
    return compiled


@router.get("/{scene_id}/state", response_model=SceneDramaStateRead)
def get_scene_state(scene_id: UUID, db: Session = Depends(get_db)) -> SceneDramaStateRead:
    row = db.query(DramaSceneState).filter(DramaSceneState.scene_id == scene_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene drama state not found")
    return row


@router.get("/{scene_id}/subtext", response_model=List[DialogueSubtextRead])
def get_scene_subtext(scene_id: UUID, db: Session = Depends(get_db)) -> List[DialogueSubtextRead]:
    return (
        db.query(DramaDialogueSubtext)
        .filter(DramaDialogueSubtext.scene_id == scene_id)
        .order_by(DramaDialogueSubtext.line_index.asc())
        .all()
    )


@router.get("/{scene_id}/blocking", response_model=BlockingPlanRead)
def get_scene_blocking(scene_id: UUID, db: Session = Depends(get_db)) -> BlockingPlanRead:
    row = db.query(DramaBlockingPlan).filter(DramaBlockingPlan.scene_id == scene_id).first()
    if row is None or row.payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blocking plan not found")
    return BlockingPlanRead(**row.payload)


@router.get("/{scene_id}/camera-plan", response_model=CameraPlanRead)
def get_scene_camera_plan(scene_id: UUID, db: Session = Depends(get_db)) -> CameraPlanRead:
    row = db.query(DramaCameraPlan).filter(DramaCameraPlan.scene_id == scene_id).first()
    if row is None or row.payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera plan not found")
    return CameraPlanRead(**row.payload)


@router.post("/{scene_id}/apply-outcome", status_code=status.HTTP_202_ACCEPTED)
def apply_scene_outcome(
    scene_id: UUID,
    payload: ApplySceneOutcomeRequest,
    db: Session = Depends(get_db),
) -> dict:
    result = ContinuityService().apply_scene_outcome(
        db=db,
        scene_id=scene_id,
        outcome_type=payload.outcome_type,
        turning_point=payload.turning_point,
        trust_shift_delta=payload.trust_shift_delta,
        exposure_shift_delta=payload.exposure_shift_delta,
        dependency_shift_delta=payload.dependency_shift_delta,
        recompute_downstream=payload.recompute_downstream,
    )
    db.commit()
    return result


@router.get("/{scene_id}/power-shifts", response_model=List[PowerShiftRead])
def get_scene_power_shifts(scene_id: UUID, db: Session = Depends(get_db)) -> List[PowerShiftRead]:
    return db.query(DramaPowerShift).filter(DramaPowerShift.scene_id == scene_id).all()
