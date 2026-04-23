"""avatar_relationship_state — SQLAlchemy model for avatar ↔ entity relationship."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarRelationshipState(Base):
    """Dynamic relationship scores between an avatar and another named entity.

    Rows are upserted by AvatarRelationshipEngine after each scene outcome.
    """

    __tablename__ = "avatar_relationship_state"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    avatar_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    target_entity_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)

    trust_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    fear_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    dominance_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    resentment_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    attraction_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    dependency_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, onupdate=_now
    )
