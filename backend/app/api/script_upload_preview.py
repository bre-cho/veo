from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.script_ingestion import parse_script_file_bytes, validate_script_file
from app.services.brain.brain_intake_service import BrainIntakeService

router = APIRouter(tags=["script-upload-preview"])
_brain_intake_service = BrainIntakeService()


@router.post("/api/v1/script-upload/preview")
async def script_upload_preview(
    file: UploadFile = File(...),
    aspect_ratio: str = Form("9:16"),
    target_platform: str = Form("shorts"),
    style_preset: str | None = Form(default=None),
    avatar_id: str | None = Form(default=None),
    market_code: str | None = Form(default=None),
    content_goal: str | None = Form(default=None),
    conversion_mode: str | None = Form(default=None),
    series_id: str | None = Form(default=None),
    episode_index: int | None = Form(default=None),
    db: Session = Depends(get_db),
):
    try:
        content = await file.read()
        ext = validate_script_file(file.filename or "", content)
        script_text = parse_script_file_bytes(ext, content)
        preview = _brain_intake_service.orchestrate_script_preview(
            db,
            filename=file.filename,
            script_text=script_text,
            aspect_ratio=aspect_ratio,
            target_platform=target_platform,
            style_preset=style_preset,
            avatar_id=avatar_id,
            market_code=market_code,
            content_goal=content_goal,
            conversion_mode=conversion_mode,
            series_id=series_id,
            episode_index=episode_index,
        )
        return {
            "ok": True,
            "data": preview,
            "error": None,
            "meta": {
                "scene_count": len(preview.get("scenes") or []),
                "subtitle_count": len(preview.get("subtitle_segments") or []),
                "series_id": preview.get("series_id"),
                "episode_index": preview.get("episode_index"),
                "episode_role": (preview.get("brain_plan") or {}).get("episode_role"),
            },
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to build script preview") from exc

