from __future__ import annotations
import logging
from sqlalchemy.orm import Session
from app.services.project_workspace_service import load_project, save_project
from app.services.provider_scene_planner import plan_provider_scenes
from app.services.execution_bridge_service import ExecutionBridgeService
from app.services.render_repository import create_render_job_with_scenes, get_render_job_by_id, build_render_job_response
from app.services.render_queue import enqueue_render_dispatch
from app.services.render_events import build_project_render_event_summary
from app.services.template_feedback_loop import maybe_enqueue_template_extraction

PROJECT_RENDER_BLOCKING_STATUSES = {"render_queued", "rendering"}
_log = logging.getLogger(__name__)
_execution_bridge = ExecutionBridgeService()

def can_render_project(project: dict) -> tuple[bool, list[str]]:
    reasons=[]; scenes=project.get("scenes") or []; subtitle_segments=project.get("subtitle_segments") or []
    if not scenes: reasons.append("Project has no scenes")
    if not subtitle_segments: reasons.append("Project has no subtitle segments")
    if project.get("status") in PROJECT_RENDER_BLOCKING_STATUSES: reasons.append(f"Project is already in status {project.get('status')}")
    for idx, scene in enumerate(scenes, start=1):
        if not scene.get("script_text"): reasons.append(f"Scene {idx} is missing script_text")
        if not scene.get("title"): reasons.append(f"Scene {idx} is missing title")
    return (len(reasons) == 0, reasons)

def trigger_project_render(db: Session, project_id: str) -> dict:
    project = load_project(project_id)
    if project is None: raise ValueError("Project not found")
    ok, reasons = can_render_project(project)
    if not ok: raise ValueError("; ".join(reasons))
    veo_config = project.get("veo_config") or {}
    bridge_ctx = _execution_bridge.resolve_project_context(db, project)
    planned_scenes=[]
    for scene in project.get("scenes", []):
        bridged_scene = _execution_bridge.apply_to_project_scene(scene, bridge_ctx)
        planned_scenes.append({
            "scene_index": bridged_scene["scene_index"],
            "title": bridged_scene["title"],
            "script_text": bridged_scene.get("script_text"),
            "prompt_text": bridged_scene.get("visual_prompt") or bridged_scene.get("script_text") or bridged_scene["title"],
            "provider_target_duration_sec": int(round(float(bridged_scene.get("target_duration_sec", 5)))),
            "aspect_ratio": project.get("format","9:16"),
            "provider_mode": bridged_scene.get("provider_mode") or veo_config.get("veo_mode"),
            "start_image_url": bridged_scene.get("start_image_url"),
            "end_image_url": bridged_scene.get("end_image_url"),
            "character_reference_image_urls": bridged_scene.get("character_reference_image_urls") or [],
            "character_reference_pack_id": veo_config.get("character_reference_pack_id"),
            "sound_generation": veo_config.get("sound_generation", False),
            "provider_model": veo_config.get("provider_model"),
        })
    try:
        planned_scenes = plan_provider_scenes(
            planned_scenes,
            project.get("provider","veo"),
            execution_context=bridge_ctx,
        )
    except ValueError as exc:
        _log.warning(
            "Provider scene planning failed for project %s (provider=%s): %s",
            project_id,
            project.get("provider", "veo"),
            exc,
        )
    job = create_render_job_with_scenes(db, project_id=project_id, provider=project.get("provider","veo"), aspect_ratio=project.get("format","9:16"), style_preset=project.get("style_preset"), subtitle_mode="burn", planned_scenes=planned_scenes)
    enqueue_render_dispatch(job.id)
    project["status"]="render_queued"; project["render_job_id"]=job.id; project.setdefault("is_template_source", True); project.setdefault("template_extracted", False)
    save_project(project)
    return {"render_job_id": job.id, "status": "queued"}

def get_project_render_status(db: Session, project_id: str) -> dict:
    project = load_project(project_id)
    if project is None: raise ValueError("Project not found")
    job_id = project.get("render_job_id")
    if not job_id:
        return {"project_id": project_id, "project_status": project.get("status","draft"), "render_status": "not_started", "progress_percent": 0, "current_step": None, "scene_statuses": [], "fail_reason": None}
    job = get_render_job_by_id(db, job_id)
    if job is None:
        return {"project_id": project_id, "project_status": project.get("status","draft"), "render_status": "missing_job", "progress_percent": 0, "current_step": None, "scene_statuses": [], "fail_reason": None}
    data = build_render_job_response(db, job, include_scenes=True)
    status_map={"queued":"render_queued","submitted":"rendering","processing":"rendering","merging":"rendering","burning_subtitles":"rendering","completed":"final_ready","failed":"render_failed"}
    project["status"]=status_map.get(data.status, project.get("status","draft"))
    if data.status == "completed":
        project["preview_video_url"]=data.final_video_url
        project["final_video_url"]=data.final_video_url or data.output_url
        project["thumbnail_url"]=data.thumbnail_url
        maybe_enqueue_template_extraction(project)
    save_project(project)
    scene_statuses=[{"scene_task_id": scene.id, "scene_index": scene.scene_index, "status": scene.status, "provider": scene.provider, "error_message": scene.error_message} for scene in data.scenes]
    progress=round(((data.completed_scene_count + data.failed_scene_count) / data.planned_scene_count)*100, 2) if data.planned_scene_count else 0
    current_step={"queued":"PREPARE_RENDER_MANIFEST","submitted":"GENERATE_SCENE_AUDIO_VISUALS","processing":"GENERATE_SCENE_AUDIO_VISUALS","merging":"RENDER_PREVIEW_VIDEO","burning_subtitles":"BURN_SUBTITLES","completed":"RENDER_FINAL_VIDEO","failed":"FAILED"}.get(data.status)
    return {"project_id": project_id, "project_status": project.get("status"), "render_job_id": job_id, "render_status": data.status, "progress_percent": progress, "current_step": current_step, "scene_statuses": scene_statuses, "preview_video_url": data.final_video_url, "final_video_url": data.final_video_url or data.output_url, "thumbnail_url": data.thumbnail_url, "fail_reason": data.error_message}

def retry_project_render(db: Session, project_id: str) -> dict:
    project = load_project(project_id)
    if project is None: raise ValueError("Project not found")
    project["status"]="ready_to_render"; save_project(project); return trigger_project_render(db, project_id)

def rerender_scene(db: Session, project_id: str, scene_index: int) -> dict:
    project = load_project(project_id)
    if project is None: raise ValueError("Project not found")
    found=False
    for scene in project.get("scenes", []):
        if int(scene.get("scene_index")) == int(scene_index):
            scene["status"]="ready"; found=True; break
    if not found: raise ValueError("Scene not found")
    save_project(project)
    return trigger_project_render(db, project_id)
