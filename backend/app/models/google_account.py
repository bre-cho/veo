from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class GoogleAccount(Base):
    __tablename__ = "google_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    gemini_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_cloud_project: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_cloud_location: Mapped[str] = mapped_column(Text, nullable=False, default="global")
    gcs_output_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    use_vertex: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rotation_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
