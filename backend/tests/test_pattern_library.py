from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.pattern_memory import PatternMemory
from app.schemas.patterns import PatternMemoryIn
from app.services.pattern_library import PatternLibrary


def _db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[PatternMemory.__table__])
    Session = sessionmaker(bind=engine)
    return Session()


def test_save_pattern() -> None:
    db = _db_session()
    lib = PatternLibrary()
    row = lib.save(
        db,
        PatternMemoryIn(
            pattern_type="hook",
            market_code="vi-VN",
            content_goal="conversion",
            payload={"text": "Question-first hook"},
            score=0.9,
        ),
    )
    assert row.id


def test_retrieve_by_market_goal_type() -> None:
    db = _db_session()
    lib = PatternLibrary()
    lib.save(db, PatternMemoryIn(pattern_type="hook", market_code="vi-VN", content_goal="conversion", payload={"a": 1}, score=0.6))
    lib.save(db, PatternMemoryIn(pattern_type="hook", market_code="en-US", content_goal="conversion", payload={"a": 2}, score=0.8))
    rows = lib.list(db, pattern_type="hook", market_code="vi-VN", content_goal="conversion")
    assert len(rows) == 1


def test_ordering_by_score_or_created_at() -> None:
    db = _db_session()
    lib = PatternLibrary()
    lib.save(db, PatternMemoryIn(pattern_type="hook", payload={"a": 1}, score=0.2))
    lib.save(db, PatternMemoryIn(pattern_type="hook", payload={"a": 2}, score=0.9))
    rows = lib.list(db, pattern_type="hook")
    assert float(rows[0].score) >= float(rows[1].score)
