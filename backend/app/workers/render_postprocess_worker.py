from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.final_timeline_builder import build_final_preview_timeline
from app.services.render_repository import (
    finalize_render_job,
    get_render_job_by_id,
    list_successful_scene_tasks,
    mark_job_status,
    stage_render_job_for_identity_review,
)
from app.services.subtitle_burner import burn_subtitles, write_srt
from app.services.video_merger import merge_clips_concat


TERMINAL_JOB_STATUSES = {"completed", "failed"}
ACTIVE_POSTPROCESS_JOB_STATUSES = {"merging", "burning_subtitles"}
logger = logging.getLogger(__name__)


def _is_job_terminal(job) -> bool:
    return job.status in TERMINAL_JOB_STATUSES


def _is_job_already_in_postprocess(job) -> bool:
    return job.status in ACTIVE_POSTPROCESS_JOB_STATUSES


def _should_fail_due_to_partial_success(job) -> bool:
    return job.failed_scene_count > 0


def _job_output_dir(job_id: str) -> Path:
    return Path(settings.render_output_dir) / job_id


def _join_public_url(*parts: str) -> str:
    base = "/" if settings.storage_public_base_url == "/" else settings.storage_public_base_url.rstrip("/")
    suffix = "/".join(p.strip("/") for p in parts if p and p.strip("/"))
    if suffix:
        return f"/{suffix}" if not base else f"{base}/{suffix}"
    return base or "/"


def _build_output_url(job_id: str, filename: str) -> str:
    render_output_dir = Path(settings.render_output_dir)
    storage_root = Path(settings.storage_root)

    try:
        relative_output_dir = render_output_dir.relative_to(storage_root)
        mapped_dir = relative_output_dir.as_posix().strip("/")
    except ValueError:
        logger.warning(
            "Render output directory is not under storage root; falling back to output directory name mapping.",
            extra={
                "render_output_dir": str(render_output_dir),
                "storage_root": str(storage_root),
            },
        )
        mapped_dir = render_output_dir.name.strip("/")

    return _join_public_url(mapped_dir, job_id, filename)


def _normalize_subtitle_segments(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    normalized: list[dict] = []
    for seg in value:
        if not isinstance(seg, dict):
            continue
        if {"start_sec", "end_sec", "text"} - seg.keys():
            continue
        try:
            start_sec = float(seg["start_sec"])
            end_sec = float(seg["end_sec"])
            text = str(seg["text"])
        except (TypeError, ValueError):
            continue
        if end_sec <= start_sec:
            continue
        normalized.append({"start_sec": start_sec, "end_sec": end_sec, "text": text})
    return normalized


async def process_render_postprocess(db: Session, job_id: str) -> None:
    job = get_render_job_by_id(db, job_id, with_scenes=False)
    if not job:
        return

    if _is_job_terminal(job):
        return

    if _is_job_already_in_postprocess(job):
        return

    if _should_fail_due_to_partial_success(job):
        mark_job_status(
            db,
            job,
            "failed",
            "Postprocess blocked by partial success policy: all scenes must succeed before final merge.",
            source="postprocess",
            reason="partial_success_policy",
        )
        return

    successful_scenes = list_successful_scene_tasks(db, job_id)

    if not successful_scenes:
        mark_job_status(
            db,
            job,
            "failed",
            "No successful scenes available for postprocess.",
            source="postprocess",
            reason="no_successful_scenes",
        )
        return

    if len(successful_scenes) != job.planned_scene_count:
        mark_job_status(
            db,
            job,
            "failed",
            (
                "Postprocess blocked: successful scene count does not match planned_scene_count "
                f"({len(successful_scenes)}/{job.planned_scene_count})."
            ),
            source="postprocess",
            reason="successful_scene_count_mismatch",
        )
        return

    updated = mark_job_status(
        db,
        job,
        "merging",
        source="postprocess",
        reason="postprocess_started",
    )
    if not updated:
        return

    out_dir = _job_output_dir(job.id)
    out_dir.mkdir(parents=True, exist_ok=True)

    video_paths = [scene.local_video_path for scene in successful_scenes if scene.local_video_path]

    if len(video_paths) != len(successful_scenes):
        mark_job_status(
            db,
            job,
            "failed",
            "Postprocess blocked: one or more successful scenes are missing local_video_path.",
            source="postprocess",
            reason="missing_local_video_path",
        )
        return

    # Check if all files are real (non-zero) video files. If they are empty stubs
    # (as created by the mock asset_collector), skip ffmpeg and use the first
    # scene's output_video_url directly as the final URL.
    file_paths = [Path(p) for p in video_paths]
    missing_paths = [str(path) for path in file_paths if not path.exists()]
    if missing_paths:
        mark_job_status(
            db,
            job,
            "failed",
            "Postprocess blocked: one or more local video files are missing.",
            source="postprocess",
            reason="missing_local_video_file",
            metadata={"missing_paths": missing_paths},
        )
        return

    all_stub = all(path.stat().st_size == 0 for path in file_paths)
    subtitle_segments = _normalize_subtitle_segments(job.subtitle_segments)
    if all_stub:
        fallback_url = next(
            (s.output_video_url for s in successful_scenes if s.output_video_url),
            _build_output_url(job.id, "mock-output.mp4"),
        )
        final_timeline = build_final_preview_timeline(
            scenes=[
                {
                    "scene_index": s.scene_index,
                    "title": s.title,
                    "video_url": s.output_video_url,
                    "local_video_path": s.local_video_path,
                }
                for s in successful_scenes
            ],
            subtitle_segments=subtitle_segments,
            merged_video_url=fallback_url,
        )
        latest_job = get_render_job_by_id(db, job_id, with_scenes=False)
        if not latest_job or _is_job_terminal(latest_job):
            return
        staged = stage_render_job_for_identity_review(
            db,
            latest_job,
            final_video_url=fallback_url,
            final_video_path=video_paths[0],
            final_timeline=final_timeline,
            source="postprocess",
        )
        if staged:
            from app.services.render_queue import enqueue_render_identity_review
            enqueue_render_identity_review(latest_job.id)
        return

    merged_path = str(out_dir / "merged.mp4")
    merge_clips_concat(video_paths, merged_path)

    final_path = merged_path

    if job.subtitle_mode == "burn" and subtitle_segments:
        updated = mark_job_status(
            db,
            job,
            "burning_subtitles",
            source="postprocess",
            reason="subtitle_burn_started",
        )
        if not updated:
            return

        srt_path = str(out_dir / "subtitles.srt")
        write_srt(subtitle_segments, srt_path)

        burned_path = str(out_dir / "merged_burned.mp4")
        burn_subtitles(merged_path, srt_path, burned_path)
        final_path = burned_path

    final_video_url = _build_output_url(job.id, Path(final_path).name)

    final_timeline = build_final_preview_timeline(
        scenes=[
            {
                "scene_index": s.scene_index,
                "title": s.title,
                "video_url": s.output_video_url,
                "local_video_path": s.local_video_path,
            }
            for s in successful_scenes
        ],
        subtitle_segments=subtitle_segments,
        merged_video_url=final_video_url,
    )

    latest_job = get_render_job_by_id(db, job_id, with_scenes=False)
    if not latest_job:
        return

    if _is_job_terminal(latest_job):
        return

    if _is_job_already_in_postprocess(latest_job) or latest_job.status == "polling":
        staged = stage_render_job_for_identity_review(
            db,
            latest_job,
            final_video_url=final_video_url,
            final_video_path=final_path,
            final_timeline=final_timeline,
            source="postprocess",
        )
        if not staged:
            return

        # Enqueue the mandatory identity review gate
        from app.services.render_queue import enqueue_render_identity_review
        enqueue_render_identity_review(latest_job.id)

        # Brain Layer feedback: record render outcome to EpisodeMemory
        try:
            from app.services.brain.brain_feedback_service import BrainFeedbackService
            from app.services.project_workspace_service import load_project
            _brain_feedback = BrainFeedbackService()
            project = load_project(latest_job.project_id) or {}
            _brain_feedback.record_render_outcome(
                db,
                project=project,
                render_job_id=latest_job.id,
                final_video_url=final_video_url,
                status="completed",
            )
        except Exception as _brain_exc:
            logger.warning("Brain feedback (render): %s", _brain_exc)
