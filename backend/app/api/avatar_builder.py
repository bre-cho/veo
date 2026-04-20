from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.avatar_builder import (
    AvatarBuilderStartRequest,
    AvatarBuilderStartResponse,
    AvatarMotionDnaUpsert,
    AvatarPreviewRequest,
    AvatarPreviewResponse,
    AvatarSaveDnaRequest,
    AvatarVisualDnaUpsert,
    AvatarVoiceDnaUpsert,
)
from app.services.avatar.avatar_builder_service import AvatarBuilderService
from app.services.avatar.avatar_clone_service import AvatarCloneService
from app.services.avatar.avatar_identity_service import AvatarIdentityService
from app.services.avatar.avatar_preview_service import AvatarPreviewService
from app.services.avatar.avatar_publish_service import AvatarPublishService
from app.repositories.avatar_repo import AvatarRepo

router = APIRouter(prefix="/api/v1/avatar-builder", tags=["avatar-builder"])

_builder = AvatarBuilderService()
_identity = AvatarIdentityService()
_publish = AvatarPublishService()
_preview = AvatarPreviewService()
_clone = AvatarCloneService()
_repo = AvatarRepo()


@router.post("/start", response_model=AvatarBuilderStartResponse)
def start_builder(req: AvatarBuilderStartRequest, db: Session = Depends(get_db)):
    return _builder.start(db, req)


@router.post("/identity")
def upsert_identity(avatar_id: str, data: dict[str, Any], db: Session = Depends(get_db)):
    result = _identity.upsert_identity(db, avatar_id, data)
    return {"ok": True, "avatar_id": result.id}


@router.post("/visual")
def upsert_visual(avatar_id: str, data: AvatarVisualDnaUpsert, db: Session = Depends(get_db)):
    result = _identity.upsert_visual(db, avatar_id, data.model_dump(exclude_none=True))
    return {"ok": True, "avatar_id": avatar_id}


@router.post("/voice")
def upsert_voice(avatar_id: str, data: AvatarVoiceDnaUpsert, db: Session = Depends(get_db)):
    _identity.upsert_voice(db, avatar_id, data.model_dump(exclude_none=True))
    return {"ok": True, "avatar_id": avatar_id}


@router.post("/motion")
def upsert_motion(avatar_id: str, data: AvatarMotionDnaUpsert, db: Session = Depends(get_db)):
    _identity.upsert_motion(db, avatar_id, data.model_dump(exclude_none=True))
    return {"ok": True, "avatar_id": avatar_id}


@router.post("/preview/static", response_model=AvatarPreviewResponse)
def preview_static(req: AvatarPreviewRequest, db: Session = Depends(get_db)):
    result = _preview.preview_static(db, req.avatar_id)
    return AvatarPreviewResponse(
        avatar_id=req.avatar_id,
        preview_url=result.get("preview_url"),
        mode="static",
        status="ok" if result.get("ok") else "error",
    )


@router.post("/preview/animated", response_model=AvatarPreviewResponse)
def preview_animated(req: AvatarPreviewRequest, db: Session = Depends(get_db)):
    result = _preview.preview_animated(db, req.avatar_id, req.script_text)
    return AvatarPreviewResponse(
        avatar_id=req.avatar_id,
        preview_url=result.get("preview_url"),
        mode="animated",
        status="ok" if result.get("ok") else "error",
    )


@router.post("/preview/lipsync", response_model=AvatarPreviewResponse)
def preview_lipsync(req: AvatarPreviewRequest, db: Session = Depends(get_db)):
    result = _preview.preview_animated(db, req.avatar_id, req.script_text)
    return AvatarPreviewResponse(
        avatar_id=req.avatar_id,
        preview_url=result.get("preview_url"),
        mode="lipsync",
        status="ok" if result.get("ok") else "error",
    )


@router.post("/save-dna")
def save_dna(req: AvatarSaveDnaRequest, db: Session = Depends(get_db)):
    visual = req.visual.model_dump(exclude_none=True) if req.visual else None
    voice = req.voice.model_dump(exclude_none=True) if req.voice else None
    motion = req.motion.model_dump(exclude_none=True) if req.motion else None
    return _builder.save_dna(db, req.avatar_id, visual, voice, motion)


@router.post("/publish")
def publish_avatar(avatar_id: str, db: Session = Depends(get_db)):
    return _publish.publish(db, avatar_id)


@router.post("/clone")
def clone_avatar(
    avatar_id: str,
    new_name: Optional[str] = None,
    owner_user_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return _clone.clone(db, avatar_id, new_name, owner_user_id)


@router.get("/{avatar_id}")
def get_avatar(avatar_id: str, db: Session = Depends(get_db)):
    avatar = _repo.get_avatar(db, avatar_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return {
        "id": avatar.id,
        "name": avatar.name,
        "role_id": avatar.role_id,
        "niche_code": avatar.niche_code,
        "market_code": avatar.market_code,
        "is_published": avatar.is_published,
        "is_featured": avatar.is_featured,
    }


# ---------------------------------------------------------------------------
# Render-time identity verification  (Trục 1)
# ---------------------------------------------------------------------------


class VerifyRenderRequest(BaseModel):
    render_url: str = Field(..., description="URL of the completed render output")
    frame_count: int = Field(default=0, ge=0, description="Number of frames in the render")
    frame_embeddings: list[list[float]] | None = Field(
        default=None,
        description="Per-frame embedding vectors (optional; enables cosine-similarity check)",
    )


@router.post("/{avatar_id}/verify-render")
def verify_render(
    avatar_id: str,
    req: VerifyRenderRequest,
    db: Session = Depends(get_db),
):
    """Verify that a completed render is consistent with the avatar's identity.

    When ``frame_embeddings`` is provided, each frame is compared against the
    avatar's canonical embedding via cosine similarity.  When the overall
    ``consistency_score`` falls below the threshold the response includes
    ``action='identity_review'`` which the caller can use to trigger an FSM
    transition to the ``identity_review`` state.
    """
    result = _identity.verify_render_output(
        db=db,
        avatar_id=avatar_id,
        render_url=req.render_url,
        frame_count=req.frame_count,
        frame_embeddings=req.frame_embeddings,
    )
    return result

