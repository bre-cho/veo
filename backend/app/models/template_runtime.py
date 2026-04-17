from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import Text, Integer, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

def uuid_col():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

class TemplateScore(Base):
    __tablename__ = "template_scores"
    id: Mapped[uuid.UUID] = uuid_col()
    template_pack_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("template_packs.id", ondelete="CASCADE"), nullable=False)
    render_score: Mapped[float] = mapped_column(Numeric(5,2), nullable=False, default=0)
    upload_score: Mapped[float] = mapped_column(Numeric(5,2), nullable=False, default=0)
    retention_score: Mapped[float] = mapped_column(Numeric(5,2), nullable=False, default=0)
    final_priority_score: Mapped[float] = mapped_column(Numeric(5,2), nullable=False, default=0)
    runs_considered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    snapshot_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_version: Mapped[str] = mapped_column(Text, nullable=False, default="v1")
    scoring_window: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight_profile: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    score_details_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class TemplateMemory(Base):
    __tablename__ = "template_memory"
    id: Mapped[uuid.UUID] = uuid_col()
    template_pack_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("template_packs.id", ondelete="CASCADE"), nullable=False, unique=True)
    state: Mapped[str] = mapped_column(Text, nullable=False, default="candidate")
    previous_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_score: Mapped[float | None] = mapped_column(Numeric(5,2), nullable=True)
    transition_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    demoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dominant_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stats_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class TemplateSelectionDecision(Base):
    __tablename__ = "template_selection_decisions"
    id: Mapped[uuid.UUID] = uuid_col()
    template_pack_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("template_packs.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    decision_mode: Mapped[str] = mapped_column(Text, nullable=False, default="recommend")
    request_context_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    fit_score: Mapped[float] = mapped_column(Numeric(5,2), nullable=False, default=0)
    reason_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    alternatives_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    outcome_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))




class TemplateEvolutionEvent(Base):
    """Event representing template evolution and learning"""
    __tablename__ = "template_evolution_events"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    old_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    performance_delta: Mapped[float | None] = mapped_column(Numeric(5,2), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class TemplateExtractedDraft(Base):
    """Extracted template draft from source project"""
    __tablename__ = "template_extracted_drafts"
    
    id: Mapped[uuid.UUID] = uuid_col()
    source_project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    extraction_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    draft_content_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    draft_version: Mapped[str] = mapped_column(Text, nullable=False, default="v1")
    is_candidate: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TemplateExtractionJob(Base):
    """Async extraction job for templates"""
    __tablename__ = "template_extraction_jobs"
    
    id: Mapped[uuid.UUID] = uuid_col()
    source_project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    auto_publish: Mapped[bool] = mapped_column(nullable=False, default=False)
    extracted_draft_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("template_extracted_drafts.id", ondelete="SET NULL"), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TemplateCompetitionRecord(Base):
    """Record template competing against others"""
    __tablename__ = "template_competition_records"
    
    id: Mapped[uuid.UUID] = uuid_col()
    template_pack_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("template_packs.id", ondelete="CASCADE"), nullable=False)
    competitor_pack_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("template_packs.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    win_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    loss_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tie_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    win_rate: Mapped[float] = mapped_column(Numeric(5,3), nullable=False, default=0.0)
    last_compared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class TemplateLearningStat(Base):
    """Learning statistics for template optimization"""
    __tablename__ = "template_learning_stats"
    
    id: Mapped[uuid.UUID] = uuid_col()
    template_pack_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("template_packs.id", ondelete="CASCADE"), nullable=False, unique=True)
    total_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    successful_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_render_quality: Mapped[float] = mapped_column(Numeric(5,3), nullable=False, default=0.0)
    avg_user_satisfaction: Mapped[float] = mapped_column(Numeric(5,3), nullable=False, default=0.0)
    recommendation_score: Mapped[float] = mapped_column(Numeric(5,3), nullable=False, default=0.0)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class TemplateReusePreview(Base):
    """Preview of template for reuse scenarios"""
    __tablename__ = "template_reuse_previews"
    
    id: Mapped[uuid.UUID] = uuid_col()
    source_draft_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("template_extracted_drafts.id", ondelete="SET NULL"), nullable=True)
    target_project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    preview_content_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    fit_score: Mapped[float] = mapped_column(Numeric(5,3), nullable=False, default=0.0)
    adaptation_hints_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
