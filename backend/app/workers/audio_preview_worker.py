from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.audio_preview_job import AudioPreviewJob
from app.services.audio.elevenlabs_adapter import ElevenLabsAdapter
from app.services.object_storage import upload_file_to_object_storage

logger = logging.getLogger(__name__)

_ARTIFACTS_AUDIO_DIR = Path("/app/artifacts/audio")


async def _run_preview(job_id: str) -> AudioPreviewJob | None:
    db = SessionLocal()
    try:
        job = db.query(AudioPreviewJob).filter(AudioPreviewJob.id == job_id).first()
        if job is None:
            logger.error("AudioPreviewJob %s not found", job_id)
            return None

        job.status = "processing"
        db.commit()

        try:
            from app.models.voice_profile import VoiceProfile

            profile = db.query(VoiceProfile).filter(VoiceProfile.id == job.voice_profile_id).first()
            if profile is None or not profile.provider_voice_id:
                raise ValueError(f"Voice profile {job.voice_profile_id} not found or missing provider_voice_id")

            adapter = ElevenLabsAdapter()
            audio_bytes = await adapter.synthesize_speech(voice_id=profile.provider_voice_id, text=job.text)

            preview_filename = f"{uuid.uuid4().hex}.mp3"
            storage_key = f"audio/previews/{preview_filename}"

            preview_dir = _ARTIFACTS_AUDIO_DIR / "previews"
            preview_dir.mkdir(parents=True, exist_ok=True)
            local_path = preview_dir / preview_filename
            local_path.write_bytes(audio_bytes)

            artifacts_root = Path("/app/artifacts")
            try:
                relative_path = local_path.relative_to(artifacts_root)
                local_fallback_url = f"/artifacts/{relative_path}"
            except ValueError:
                local_fallback_url = f"/artifacts/audio/previews/{preview_filename}"

            preview_url: str
            try:
                stored = upload_file_to_object_storage(
                    local_path=str(local_path), key=storage_key, content_type="audio/mpeg"
                )
                preview_url = stored.public_url or local_fallback_url
            except Exception:
                logger.warning("Failed to upload audio preview to object storage; using local URL", exc_info=True)
                preview_url = local_fallback_url

            job.status = "succeeded"
            job.preview_url = preview_url
        except Exception as exc:
            logger.exception("AudioPreviewJob %s failed: %s", job_id, exc)
            job.status = "failed"
            job.error_message = str(exc)

        db.commit()
        db.refresh(job)
        return job
    finally:
        db.close()


@celery_app.task(name="audio.run_preview")
def run_audio_preview_task(job_id: str) -> dict:
    job = asyncio.run(_run_preview(job_id))
    if job is None:
        return {"ok": False, "error": "job not found"}
    return {"ok": job.status == "succeeded", "job_id": job.id, "status": job.status, "preview_url": job.preview_url}
