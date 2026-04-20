from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.patterns import PatternMemoryIn, PatternMemoryOut
from app.services.pattern_library import PatternLibrary

router = APIRouter(prefix="/api/v1/patterns", tags=["patterns"])

_library = PatternLibrary()


@router.post("", response_model=PatternMemoryOut)
def create_pattern(payload: PatternMemoryIn, db: Session = Depends(get_db)) -> PatternMemoryOut:
    row = _library.save(db, payload)
    return PatternMemoryOut(
        pattern_id=row.id,
        pattern_type=row.pattern_type,
        market_code=row.market_code,
        content_goal=row.content_goal,
        payload=row.payload,
        score=float(row.score) if row.score is not None else None,
        created_at=row.created_at.isoformat(),
    )


@router.get("", response_model=list[PatternMemoryOut])
def list_patterns(
    pattern_type: str | None = None,
    market_code: str | None = None,
    content_goal: str | None = None,
    db: Session = Depends(get_db),
) -> list[PatternMemoryOut]:
    rows = _library.list(
        db,
        pattern_type=pattern_type,
        market_code=market_code,
        content_goal=content_goal,
    )
    return [
        PatternMemoryOut(
            pattern_id=row.id,
            pattern_type=row.pattern_type,
            market_code=row.market_code,
            content_goal=row.content_goal,
            payload=row.payload,
            score=float(row.score) if row.score is not None else None,
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]
