from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.render.rerender.schemas import RerenderSceneRequest
from app.render.rerender.rerender_service import RerenderService

router = APIRouter(prefix="/api/v1/render/rerender", tags=["render-rerender"])


def _get_service() -> RerenderService:
    """Return a :class:`RerenderService` wired to the active TTS / video providers.

    Replace the stub implementations below with real service instances once the
    TTS and video provider modules are available in this service layer.
    """
    try:
        from app.services.tts_service import tts_service as _tts  # type: ignore[import]
        from app.services.video_service import video_service as _video  # type: ignore[import]
    except ImportError:
        # Fallback stubs so the endpoint is always registered even when the
        # heavyweight provider modules are not yet installed.
        class _StubTTS:
            def generate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
                raise NotImplementedError("TTS service not configured for rerender")

        class _StubVideo:
            def render_scene(self, payload: Dict[str, Any]) -> Dict[str, Any]:
                raise NotImplementedError("Video service not configured for rerender")

        _tts = _StubTTS()  # type: ignore[assignment]
        _video = _StubVideo()  # type: ignore[assignment]

    return RerenderService(tts_service=_tts, video_service=_video)


@router.post("/scene")
def rerender_scene(payload: RerenderSceneRequest) -> Dict[str, Any]:
    """Rerender a single scene from its stored manifest.

    Reads asset paths and metadata from the scene manifest, regenerates the
    requested component (``audio``, ``video``, or ``both``), updates the
    manifest, and marks ``needs_reassembly = true``.

    After this call, trigger ``POST /api/v1/render/assembly/execute`` with
    the original assembly plan to produce a fresh final MP4.
    """
    try:
        return _get_service().rerender_scene(payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
