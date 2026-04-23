from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException

from app.schemas.script_preview import ConfirmCreateProjectRequest
from app.services.project_workspace_service import PROJECT_STORAGE_DIR
from app.services.script_validation_issues import validate_preview_with_issues

router = APIRouter(tags=["projects"])


@router.post("/api/v1/projects/create-from-script-preview")
async def create_project_from_script_preview(payload: ConfirmCreateProjectRequest):
    try:
        if not payload.confirmed:
            raise HTTPException(status_code=400, detail="Confirmation required")

        preview_dict = payload.preview_payload.model_dump()
        validation_result = validate_preview_with_issues(preview_dict)
        if not validation_result.valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Preview validation failed",
                    "issues": [issue.model_dump() for issue in validation_result.issues],
                },
            )

        project_id = str(uuid.uuid4())
        project = {
            "id": project_id,
            "name": payload.name.strip(),
            "idea": (payload.idea or "Created from script upload").strip(),
            "avatar_id": payload.preview_payload.avatar_id,
            "market_code": payload.preview_payload.market_code,
            "content_goal": payload.preview_payload.content_goal,
            "conversion_mode": payload.preview_payload.conversion_mode,
            "target_platform": payload.preview_payload.target_platform,
            "format": payload.preview_payload.aspect_ratio,
            "style_preset": payload.preview_payload.style_preset,
            "status": "ready_to_render",
            "source_mode": payload.preview_payload.source_mode,
            "script_text": payload.preview_payload.script_text,
            "scenes": [scene.model_dump() for scene in payload.preview_payload.scenes],
            "subtitle_segments": [segment.model_dump() for segment in payload.preview_payload.subtitle_segments],
            "storyboard": payload.preview_payload.storyboard,
            "optimization_response": payload.preview_payload.optimization_response,
            "winner_patterns": payload.preview_payload.winner_patterns or [],
            "original_filename": payload.preview_payload.original_filename,
            # Brain Layer enrichment
            "series_id": payload.preview_payload.series_id,
            "episode_index": payload.preview_payload.episode_index,
            "brain_plan": payload.preview_payload.brain_plan,
            "continuity_context": payload.preview_payload.continuity_context,
            "winner_dna_summary": payload.preview_payload.winner_dna_summary,
            "memory_refs": payload.preview_payload.memory_refs,
            # Template System enrichment
            "selected_template_id": payload.preview_payload.selected_template_id,
            "selected_template_family": payload.preview_payload.selected_template_family,
            "is_template_source": True,
            "template_extracted": False,
            "template_extract_queued": False,
            "template_source_locked": False,
            # Avatar System enrichment
            "avatar_identity": payload.preview_payload.avatar_identity,
            "avatar_voice": payload.preview_payload.avatar_voice,
            "avatar_continuity": payload.preview_payload.avatar_continuity,
            # Avatar Acting Model enrichment
            "avatar_acting_profile": getattr(payload.preview_payload, "avatar_acting_profile", None),
            "acting_payload": getattr(payload.preview_payload, "acting_payload", None),
        }

        project_dir = PROJECT_STORAGE_DIR / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
        (project_dir / "script.txt").write_text(project["script_text"], encoding="utf-8")

        return {
            "ok": True,
            "data": project,
            "error": None,
            "meta": {
                "project_id": project_id,
                "scene_count": len(project["scenes"]),
                "subtitle_count": len(project["subtitle_segments"]),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to create project from preview") from exc
