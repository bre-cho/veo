"""avatar_tournament — debug/ops API for the avatar tournament engine."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.avatar_tournament import AvatarTournamentRequest, AvatarTournamentResult
from app.services.avatar.avatar_tournament_engine import AvatarTournamentEngine

router = APIRouter(tags=["avatar-tournament"])
_engine = AvatarTournamentEngine()


# =========================
# Request/response helpers
# =========================

class TournamentRunRequest(BaseModel):
    workspace_id: str = Field(default="debug-workspace")
    project_id: str | None = None
    market_code: str | None = None
    content_goal: str | None = None
    topic_class: str | None = None
    template_family: str | None = None
    platform: str | None = None
    candidate_avatar_ids: list[str] = Field(default_factory=list)
    exploration_ratio: float = Field(default=0.15, ge=0.0, le=1.0)
    force_avatar_ids: list[str] = Field(default_factory=list)
    preferred_avatar_id: str | None = None


# =========================
# Routes
# =========================

@router.post("/api/v1/avatar/tournament/run", response_model=dict[str, Any])
async def run_tournament(
    payload: TournamentRunRequest,
    db: Session = Depends(get_db),
):
    """Run an avatar selection tournament with the given context."""
    try:
        request = AvatarTournamentRequest(
            workspace_id=payload.workspace_id,
            project_id=payload.project_id,
            market_code=payload.market_code,
            content_goal=payload.content_goal,
            topic_class=payload.topic_class,
            template_family=payload.template_family,
            platform=payload.platform,
            candidate_avatar_ids=payload.candidate_avatar_ids,
            exploration_ratio=payload.exploration_ratio,
            force_avatar_ids=payload.force_avatar_ids,
            preferred_avatar_id=payload.preferred_avatar_id,
        )
        result = _engine.run_tournament(db=db, request=request)
        return {"ok": True, "data": result.model_dump(), "error": None}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/v1/avatar/tournament/{run_id}", response_model=dict[str, Any])
async def get_tournament_run(
    run_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve tournament run details and candidate ranking by run_id."""
    from app.models.avatar_tournament_run import AvatarTournamentRun
    from app.models.avatar_match_result import AvatarMatchResult

    run = db.query(AvatarTournamentRun).filter(AvatarTournamentRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail=f"Tournament run {run_id!r} not found")

    matches = (
        db.query(AvatarMatchResult)
        .filter(AvatarMatchResult.tournament_run_id == run_id)
        .order_by(AvatarMatchResult.selection_rank)
        .all()
    )

    selected = next((m for m in matches if m.was_published), None)

    return {
        "ok": True,
        "data": {
            "run_id": run.id,
            "project_id": run.project_id,
            "template_family": run.template_family,
            "platform": run.platform,
            "status": run.status,
            "selection_mode": run.selection_mode,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "selected_avatar_id": selected.avatar_id if selected else None,
            "candidates": [
                {
                    "rank": m.selection_rank,
                    "avatar_id": m.avatar_id,
                    "predicted_score": m.predicted_score,
                    "fitness_score": m.fitness_score,
                    "result_label": m.result_label,
                    "was_published": m.was_published,
                    "was_exploration": m.was_exploration,
                }
                for m in matches
            ],
        },
        "error": None,
    }
