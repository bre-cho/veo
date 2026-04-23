from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.avatar_tournament import AvatarTournamentRequest, AvatarTournamentResult
from app.services.avatar.avatar_tournament_engine import AvatarTournamentEngine

router = APIRouter(prefix="/avatar/tournament", tags=["avatar-tournament"])


# TODO: replace with the monorepo's real DB dependency.
def get_db():  # pragma: no cover
    raise NotImplementedError("Wire get_db from your app.db.session module")


@router.post("/run", response_model=AvatarTournamentResult)
def run_avatar_tournament(payload: AvatarTournamentRequest, db: Session = Depends(get_db)) -> AvatarTournamentResult:
    engine = AvatarTournamentEngine(db)
    return engine.run_tournament(payload)


@router.get("/{run_id}")
def get_avatar_tournament_debug(run_id: str, db: Session = Depends(get_db)) -> dict:
    # TODO: hydrate tournament run + ranked match results from DB.
    raise HTTPException(status_code=501, detail=f"Tournament debug endpoint not wired yet for run_id={run_id}")
