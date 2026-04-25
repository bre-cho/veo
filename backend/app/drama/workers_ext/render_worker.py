from __future__ import annotations

from typing import Any, Dict

from app.drama.tts.services.tts_payload_builder import build_tts_payload


def process_scene_render_job(
    job: Dict[str, Any],
    tts_service: Any,
    video_service: Any,
) -> Dict[str, Any]:
    """Process a single scene render job.

    Builds a TTS payload from the job dict, generates audio, then renders the
    video scene with the resulting audio URL.

    Args:
        job: A render job dict as produced by
            :func:`app.drama.render.services.render_job_service.create_render_job_from_script`.
        tts_service: Any object with a ``generate(payload) -> dict`` method that
            returns ``{"audio_url": str, ...}``.
        video_service: Any object with a ``render_scene(payload) -> dict`` method.

    Returns:
        The video render result dict.
    """
    tts_payload = build_tts_payload(job)
    audio_result = tts_service.generate(tts_payload)

    # Propagate word-level timestamps so the timeline compiler and subtitle
    # writer can produce accurate karaoke timing.
    job["audio_url"] = audio_result.get("audio_url")
    job["audio_duration_sec"] = audio_result.get("duration_sec")
    job["word_timings"] = audio_result.get("word_timings", [])

    drama_metadata = job.get("drama_metadata", {})

    video_result = video_service.render_scene({
        "scene_id": job.get("scene_id"),
        "duration_sec": job.get("duration_sec"),
        "audio_url": audio_result.get("audio_url"),
        "render_purpose": job.get("render_purpose"),
        "emotion": job.get("emotion") or drama_metadata.get("emotion"),
        "subtext": job.get("subtext") or drama_metadata.get("subtext"),
    })

    video_result["word_timings"] = job["word_timings"]

    return video_result
