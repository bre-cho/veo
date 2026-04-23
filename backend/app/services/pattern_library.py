from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.pattern_memory import PatternMemory
from app.schemas.patterns import PatternMemoryIn


_WINNER_PATTERN_TYPES = (
    "winner_dna",
    "scene_sequence_pattern",
    "hook_pattern",
    "title_pattern",
    "pacing_pattern",
    "cta_pattern",
)


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

    def list_winners(
        self,
        db: Session,
        *,
        market_code: str | None = None,
        content_goal: str | None = None,
        limit: int = 5,
    ) -> list[PatternMemory]:
        """Return top winner patterns ordered by score descending.

        Filters to well-known winner pattern types (winner_dna, hook_pattern,
        etc.) and optionally scopes to market_code + content_goal.  Falls back
        to global top winners when the scoped result set is empty.
        """
        query = db.query(PatternMemory).filter(
            PatternMemory.pattern_type.in_(_WINNER_PATTERN_TYPES)
        )
        scoped = query
        if market_code:
            scoped = scoped.filter(PatternMemory.market_code == market_code)
        if content_goal:
            scoped = scoped.filter(PatternMemory.content_goal == content_goal)

        rows = (
            scoped
            .order_by(PatternMemory.score.is_(None), PatternMemory.score.desc(), PatternMemory.created_at.desc())
            .limit(limit)
            .all()
        )
        if rows:
            return rows

        # Fallback: global top winners ignoring market/goal scope
        return (
            query
            .order_by(PatternMemory.score.is_(None), PatternMemory.score.desc(), PatternMemory.created_at.desc())
            .limit(limit)
            .all()
        )

    def list_top_patterns(
        self,
        db: Session,
        *,
        market_code: str | None = None,
        content_goal: str | None = None,
        limit: int = 5,
        pattern_types: list[str] | None = None,
    ) -> list[PatternMemory]:
        """Return top patterns filtered by type list, scoped then global fallback.

        This is the preferred recall method for the Brain Layer.
        """
        types = pattern_types or list(_WINNER_PATTERN_TYPES)
        query = db.query(PatternMemory).filter(PatternMemory.pattern_type.in_(types))
        scoped = query
        if market_code:
            scoped = scoped.filter(PatternMemory.market_code == market_code)
        if content_goal:
            scoped = scoped.filter(PatternMemory.content_goal == content_goal)

        rows = (
            scoped
            .order_by(PatternMemory.score.is_(None), PatternMemory.score.desc(), PatternMemory.created_at.desc())
            .limit(limit)
            .all()
        )
        if rows:
            return rows

        # Fallback: global top ignoring market/goal scope
        return (
            query
            .order_by(PatternMemory.score.is_(None), PatternMemory.score.desc(), PatternMemory.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_top_pattern(
        self,
        db: Session,
        *,
        pattern_type: str = "winner_dna",
        market_code: str | None = None,
        content_goal: str | None = None,
    ) -> PatternMemory | None:
        """Return the single highest-scored pattern of the given type."""
        rows = self.list_winners(
            db,
            market_code=market_code,
            content_goal=content_goal,
            limit=1,
        )
        for row in rows:
            if row.pattern_type == pattern_type:
                return row
        # Widen search if scoped query missed the requested type
        return (
            db.query(PatternMemory)
            .filter(PatternMemory.pattern_type == pattern_type)
            .order_by(PatternMemory.score.is_(None), PatternMemory.score.desc())
            .first()
        )

