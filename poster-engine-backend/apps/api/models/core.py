import enum
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Float, Integer, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from apps.api.db.session import Base

class ProjectStatus(str, enum.Enum):
    draft = "draft"
    generating = "generating"
    scored = "scored"
    exported = "exported"
    failed = "failed"

class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"

class Brand(Base):
    __tablename__ = "brands"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    industry = Column(String, default="beauty")
    colors = Column(JSON, default=list)
    fonts = Column(JSON, default=list)
    brand_voice = Column(Text, default="luxury, premium, trustworthy")
    logo_asset_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id = Column(String, nullable=False)
    brand_id = Column(String, ForeignKey("brands.id"), nullable=False)
    campaign_type = Column(String, default="luxury_beauty")
    product_name = Column(String, nullable=False)
    target_customer = Column(String, default="women 18-35")
    offer = Column(String, default="Inbox chọn màu theo cá tính")
    status = Column(Enum(ProjectStatus), default=ProjectStatus.draft)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    brand = relationship("Brand")

class Asset(Base):
    __tablename__ = "assets"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String, nullable=False)
    storage_key = Column(String, nullable=False)
    mime_type = Column(String, default="image/png")
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    checksum = Column(String, nullable=True)
    provider = Column(String, default="mock")
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PosterVariant(Base):
    __tablename__ = "poster_variants"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    variant_type = Column(String, nullable=False)
    prompt = Column(Text, nullable=False)
    provider = Column(String, default="mock")
    image_asset_id = Column(String, nullable=True)
    canva_design_id = Column(String, nullable=True)
    adobe_asset_id = Column(String, nullable=True)
    ctr_score = Column(Float, default=0)
    attention_score = Column(Float, default=0)
    luxury_score = Column(Float, default=0)
    trust_score = Column(Float, default=0)
    product_focus = Column(Float, default=0)
    conversion_score = Column(Float, default=0)
    final_score = Column(Float, default=0)
    status = Column(String, default="created")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    project = relationship("Project")

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, nullable=True)
    job_type = Column(String, nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.queued)
    provider = Column(String, default="internal")
    input_json = Column(JSON, default=dict)
    output_json = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class BillingUsage(Base):
    __tablename__ = "billing_usage"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id = Column(String, nullable=False)
    brand_id = Column(String, ForeignKey("brands.id"), nullable=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    event_type = Column(String, nullable=False)
    units = Column(Integer, default=1)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
