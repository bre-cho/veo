from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

try:
    from app.db.base_class import Base
except Exception:  # pragma: no cover
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):  # type: ignore[no-redef]
        pass


class DramaRelationshipEdge(Base):
    """
    Directional relationship edge A -> B.

    Direction matters:
    - A trusting B does not imply B trusts A.
    - A fearing B does not imply B fears A.
    """

    __tablename__ = "drama_relationship_edges"
    __table_args__ = (
        Index(
            "ix_drama_relationship_edges_project_pair",
            "project_id",
            "source_character_id",
            "target_character_id",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    source_character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drama_character_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    target_character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drama_character_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    intimacy_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trust_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    dependence_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    fear_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    resentment_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    attraction_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rivalry_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    dominance_source_over_target: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    perceived_loyalty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hidden_agenda_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    recent_betrayal_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unresolved_tension_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)

    last_interaction_scene_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    source_character: Mapped["DramaCharacterProfile"] = relationship(  # type: ignore[name-defined]
        foreign_keys=[source_character_id]
    )
    target_character: Mapped["DramaCharacterProfile"] = relationship(  # type: ignore[name-defined]
        foreign_keys=[target_character_id]
    )
