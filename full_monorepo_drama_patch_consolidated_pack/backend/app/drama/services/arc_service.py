from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.drama.models.arc_progress import DramaArcProgress


class DramaArcService:
    """Persistence and incremental update service for character arcs."""

    def __init__(self, db: Session):
        self.db = db

    def get_latest_arc(self, character_id: UUID, episode_id: UUID | None = None) -> DramaArcProgress | None:
        stmt = select(DramaArcProgress).where(DramaArcProgress.character_id == character_id)
        if episode_id:
            stmt = stmt.where(DramaArcProgress.episode_id == episode_id)
        stmt = stmt.order_by(desc(DramaArcProgress.updated_at)).limit(1)
        return self.db.execute(stmt).scalar_one_or_none()

    def create_or_update_arc(self, payload: dict) -> DramaArcProgress:
        character_id = payload["character_id"]
        episode_id = payload.get("episode_id")
        current = self.get_latest_arc(character_id=character_id, episode_id=episode_id)
        if not current:
            current = DramaArcProgress(**payload)
            self.db.add(current)
            self.db.flush()
            return current

        for key, value in payload.items():
            setattr(current, key, value)
        self.db.add(current)
        self.db.flush()
        return current

    def build_arc_payload(self, character_id: UUID, analysis: dict, current_arc: DramaArcProgress | None) -> dict:
        current_stage = current_arc.arc_stage if current_arc else "mask_stable"
        tension = float(analysis.get("drama_state", {}).get("tension_score", 0.0))
        exposure = float(analysis.get("drama_state", {}).get("exposure_shift_delta", 0.0))
        pressure_index = min(1.0, (current_arc.pressure_index if current_arc else 0.0) + tension * 0.01)
        mask_break = min(1.0, (current_arc.mask_break_level if current_arc else 0.0) + max(0.0, exposure))

        next_stage = current_stage
        if mask_break >= 0.75:
            next_stage = "truth_encounter"
        elif mask_break >= 0.5:
            next_stage = "first_exposure"
        elif pressure_index >= 0.35 and current_stage == "mask_stable":
            next_stage = "pressure_crack"

        return {
            "project_id": analysis.get("project_id"),
            "episode_id": analysis.get("episode_id"),
            "character_id": character_id,
            "arc_name": (current_arc.arc_name if current_arc else "primary_arc"),
            "arc_stage": next_stage,
            "false_belief": current_arc.false_belief if current_arc else None,
            "pressure_index": pressure_index,
            "transformation_index": min(1.0, (current_arc.transformation_index if current_arc else 0.0) + 0.1 * max(mask_break, 0.1)),
            "collapse_risk": min(1.0, (current_arc.collapse_risk if current_arc else 0.0) + max(0.0, tension - 70.0) / 100.0),
            "mask_break_level": mask_break,
            "truth_acceptance_level": min(1.0, (current_arc.truth_acceptance_level if current_arc else 0.0) + max(0.0, exposure) * 0.5),
            "relation_entanglement_index": min(1.0, (current_arc.relation_entanglement_index if current_arc else 0.0) + 0.05),
            "latest_scene_id": analysis.get("scene_id"),
            "notes": "Auto-updated from scene analysis.",
        }
