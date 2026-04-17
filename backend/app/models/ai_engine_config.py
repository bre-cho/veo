from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Integer, Text, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AiEngineConfig(Base):
    __tablename__ = "ai_engine_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    openrouter_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_model: Mapped[str] = mapped_column(String(128), nullable=False, default="openai/gpt-4o-mini")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
