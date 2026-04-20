"""Avatar embedding extraction API endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.avatar.avatar_identity_service import AvatarIdentityService
from app.services.avatar.media_embedding_extractor import MediaEmbeddingExtractor

router = APIRouter(prefix="/api/v1/avatars", tags=["avatars"])


class EmbeddingExtractRequest(BaseModel):
    media_path: str | None = Field(default=None, description="Local path to media file")
    media_url: str | None = Field(default=None, description="URL of media file")
    n_frames: int = Field(default=8, ge=1, le=64, description="Frames to sample from video")


class EmbeddingExtractResponse(BaseModel):
    job_id: str
    avatar_id: str
    status: str
    embedding_dim: int | None = None
    updated: bool = False


@router.post("/{avatar_id}/extract-embedding", response_model=EmbeddingExtractResponse)
def extract_embedding(
    avatar_id: str,
    body: EmbeddingExtractRequest,
    db: Session = Depends(get_db),
) -> EmbeddingExtractResponse:
    """Extract an embedding from a media file and attach it to the avatar's visual DNA.

    Runs synchronously.  Returns ``{job_id, status}`` for compatibility with
    future async upgrade.
    """
    import uuid

    job_id = str(uuid.uuid4())

    media_source = body.media_path or body.media_url
    if not media_source:
        raise HTTPException(
            status_code=422,
            detail="Provide either media_path or media_url",
        )

    extractor = MediaEmbeddingExtractor()
    try:
        embedding = extractor.extract(media_source, n_frames=body.n_frames)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Embedding extraction failed: {exc}",
        ) from exc

    svc = AvatarIdentityService()
    try:
        svc.upsert_visual(db, avatar_id, {
            "embedding_vector": embedding,
            "source_media_path": media_source,
        })
        updated = True
    except Exception:
        updated = False

    return EmbeddingExtractResponse(
        job_id=job_id,
        avatar_id=avatar_id,
        status="completed",
        embedding_dim=len(embedding),
        updated=updated,
    )
