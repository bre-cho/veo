"""Common dependency helpers for FastAPI routers."""

from typing import Generator
from sqlalchemy.orm import Session
from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Provide database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
