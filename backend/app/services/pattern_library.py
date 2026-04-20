from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.pattern_memory import PatternMemory
from app.schemas.patterns import PatternMemoryIn


class PatternLibrary:
    def save(self, db: Session, payload: PatternMemoryIn) -> PatternMemory:
        row = PatternMemory(
            pattern_type=payload.pattern_type,
            market_code=payload.market_code,
            content_goal=payload.content_goal,
            source_id=payload.source_id,
            score=payload.score,
            payload=payload.payload,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def list(
        self,
        db: Session,
        *,
        pattern_type: str | None = None,
        market_code: str | None = None,
        content_goal: str | None = None,
    ) -> list[PatternMemory]:
        query = db.query(PatternMemory)
        if pattern_type:
            query = query.filter(PatternMemory.pattern_type == pattern_type)
        if market_code:
            query = query.filter(PatternMemory.market_code == market_code)
        if content_goal:
            query = query.filter(PatternMemory.content_goal == content_goal)
        return query.order_by(PatternMemory.score.is_(None), PatternMemory.score.desc(), PatternMemory.created_at.desc()).all()
