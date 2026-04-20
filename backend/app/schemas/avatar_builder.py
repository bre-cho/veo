from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class AvatarDnaCreate(BaseModel):
    name: str
    role_id: Optional[str] = None
    niche_code: Optional[str] = None
    market_code: Optional[str] = None
    owner_user_id: Optional[str] = None
    creator_id: Optional[str] = None
    tags: Optional[list[str]] = None
    meta: Optional[dict[str, Any]] = None


class AvatarDnaRead(BaseModel):
    id: str
    name: str
    role_id: Optional[str] = None
    niche_code: Optional[str] = None
    market_code: Optional[str] = None
    owner_user_id: Optional[str] = None
    creator_id: Optional[str] = None
    is_published: bool
    is_featured: bool
    tags: Optional[Any] = None
    meta: Optional[Any] = None

    model_config = {"from_attributes": True}


class AvatarVisualDnaUpsert(BaseModel):
    skin_tone: Optional[str] = None
    hair_style: Optional[str] = None
    hair_color: Optional[str] = None
    eye_color: Optional[str] = None
    outfit_code: Optional[str] = None
    background_code: Optional[str] = None
    age_range: Optional[str] = None
    gender_expression: Optional[str] = None
    accessories: Optional[list[str]] = None
    reference_image_url: Optional[str] = None


class AvatarVoiceDnaUpsert(BaseModel):
    voice_profile_id: Optional[str] = None
    language_code: Optional[str] = None
    accent_code: Optional[str] = None
    tone: Optional[str] = None
    pitch: Optional[str] = None
    speed: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class AvatarMotionDnaUpsert(BaseModel):
    motion_style: Optional[str] = None
    gesture_set: Optional[str] = None
    idle_animation: Optional[str] = None
    lipsync_mode: Optional[str] = None
    blink_rate: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class AvatarBuilderStartRequest(BaseModel):
    name: str
    role_id: Optional[str] = None
    niche_code: Optional[str] = None
    market_code: Optional[str] = None
    owner_user_id: Optional[str] = None


class AvatarBuilderStartResponse(BaseModel):
    avatar_id: str
    name: str
    status: str = "draft"


class AvatarSaveDnaRequest(BaseModel):
    avatar_id: str
    visual: Optional[AvatarVisualDnaUpsert] = None
    voice: Optional[AvatarVoiceDnaUpsert] = None
    motion: Optional[AvatarMotionDnaUpsert] = None


class AvatarPreviewRequest(BaseModel):
    avatar_id: str
    mode: str = "static"
    script_text: Optional[str] = None


class AvatarPreviewResponse(BaseModel):
    avatar_id: str
    preview_url: Optional[str] = None
    mode: str
    status: str
