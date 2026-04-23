from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.autopilot_brain import AutopilotBrainCompileRequest
from app.services.autopilot_brain_runtime import AutopilotBrainRuntime
from app.services.brain.brain_intake_service import BrainIntakeService
from app.services.script_ingestion import build_preview_payload, parse_script_file_bytes, validate_script_file

router = APIRouter(tags=["script-upload-preview"])
_brain_intake_service = BrainIntakeService()

_brain = AutopilotBrainRuntime()


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
    use_autopilot_brain: bool = Form(default=True),
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
        brain = None
        if use_autopilot_brain:
            compiled = _brain.compile(
                db=db,
                req=AutopilotBrainCompileRequest(
                    script_text=preview.get("script_text"),
                    platform=target_platform,
                    market_code=market_code,
                    niche=content_goal,
                    store_if_winner=False,
                ),
            )
            preview["autopilot_brain"] = compiled.runtime_memory_payload
            preview["youtube_seo"] = compiled.seo_bridge.model_dump()
            brain = compiled.model_dump()
        return {
            "ok": True,
            "data": preview,
            "brain": brain,
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

