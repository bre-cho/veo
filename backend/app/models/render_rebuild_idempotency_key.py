from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RenderRebuildIdempotencyKey(Base):
    """Idempotency registry for approved rebuild executions.

    Keyed by the SHA-256 fingerprint of a decision payload.  The ``result_json``
    column stores the serialised execution result so that duplicate submissions
    return the cached outcome without re-running the rebuild.
    """

    __tablename__ = "render_rebuild_idempotency_keys"

    idempotency_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
        index=True,
    )
