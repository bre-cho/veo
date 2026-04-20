"""Common dependency helpers for FastAPI routers."""

from dataclasses import dataclass
from typing import Generator
from fastapi import Header, HTTPException
from sqlalchemy.orm import Session
from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Provide database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@dataclass
class CurrentUser:
    id: str


def get_current_user(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> CurrentUser:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return CurrentUser(id=x_user_id)
