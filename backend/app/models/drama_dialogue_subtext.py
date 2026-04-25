"""drama_dialogue_subtext — per-line subtext record for the dialogue engine.

.. deprecated::
    This module is a legacy copy. Use ``app.drama.models`` instead.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DramaDialogueSubtext(Base):
    """Three-layer subtext record for a single dialogue line.

    Captures literal text, hidden intent, and psychological action for
    each spoken line in a scene.  Index: (scene_id), (speaker_id, target_id).
    """

    __tablename__ = "drama_dialogue_subtext"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    scene_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    project_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    speaker_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    line_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    literal_intent: Mapped[str | None] = mapped_column(String(256), nullable=True)
    hidden_intent: Mapped[str | None] = mapped_column(String(256), nullable=True)
    psychological_action: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Dialogue act type: attack / probe / withhold / seduce / shame / reassure /
    # dominate / retreat / bait / confess / redirect / expose / deny / test_loyalty
    dialogue_act: Mapped[str] = mapped_column(String(64), nullable=False, default="direct")

    # Emotional charge dimensions (0–1)
    emotional_charge: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    honesty_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    mask_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    threat_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    intimacy_bid: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    power_move: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expected_target_reaction: Mapped[str | None] = mapped_column(String(128), nullable=True)

    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
