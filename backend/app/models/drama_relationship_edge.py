"""drama_relationship_edge — first-class relationship object between two characters."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DramaRelationshipEdge(Base):
    """Directed relationship between ``source_character`` and ``target_character``.

    All relationship levels are from the perspective of the source character.
    The inverse direction is a separate row (or can be derived by the engine).
    """

    __tablename__ = "drama_relationship_edge"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    source_character_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    target_character_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)

    relation_type: Mapped[str] = mapped_column(String(64), nullable=False, default="neutral")

    # Relational levels (0–1 scale)
    intimacy_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    trust_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    dependence_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fear_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    resentment_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    attraction_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rivalry_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Section 7.2 core edge scores
    trust: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    fear: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    dependence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    resentment: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    attraction: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    moral_superiority: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    perceived_power: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    hidden_agenda: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    shame_exposure_risk: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    emotional_hook_strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Power dynamics
    dominance_source_over_target: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    perceived_loyalty: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    hidden_agenda_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Accumulated tension
    recent_betrayal_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unresolved_tension_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, onupdate=_now
    )
