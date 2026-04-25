from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from app.drama.script.schemas.next_level_script_request import NextLevelScriptRequest
from app.drama.script.services.next_level_script_service import NextLevelScriptService
from app.drama.render.services.render_job_service import create_render_job_from_script
from app.drama.timeline.services.timeline_service import TimelineService

router = APIRouter(prefix="/api/v1/drama/script", tags=["drama-script"])

service = NextLevelScriptService()
timeline_service = TimelineService()


@router.post("/next-level-generate")
def next_level_generate(payload: NextLevelScriptRequest) -> Dict[str, Any]:
    """Generate a next-level script with render-ready scene payloads attached."""
    return service.generate(payload)


@router.post("/next-level-generate-and-queue-render")
def generate_script_and_queue_render(payload: NextLevelScriptRequest) -> Dict[str, Any]:
    """Generate a script and build a render job queue from the resulting scenes."""
    script_output = service.generate(payload)

    render_jobs = create_render_job_from_script(
        project_id=payload.project_id,
        script_output=script_output,
    )

    return {
        "script": script_output,
        "render_jobs": render_jobs,
        "status": "queued",
    }


@router.post("/next-level-generate-render-timeline")
def generate_script_render_timeline(payload: NextLevelScriptRequest) -> Dict[str, Any]:
    """Generate a script, build render jobs, and compile a full scene timeline."""
    script_output = service.generate(payload)

    render_jobs = create_render_job_from_script(
        project_id=payload.project_id,
        script_output=script_output,
    )

    timeline = timeline_service.compiler.compile(
        project_id=payload.project_id,
        episode_id=payload.episode_id,
        render_scenes=script_output.get("render_scenes", []),
    )

    return {
        "script": script_output,
        "render_jobs": render_jobs,
        "timeline": timeline,
        "status": "timeline_compiled",
    }
