from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from app.drama.tts.services.tts_payload_builder import build_tts_payload
from app.render.manifest.manifest_service import ManifestService
from app.render.rerender.schemas import RerenderSceneRequest


class RerenderService:
    """Rerender a single scene using metadata stored in its manifest.

    Args:
        tts_service: Object with ``generate(payload: dict) -> dict``
            that returns at minimum ``{"audio_url": str}``.
        video_service: Object with ``render_scene(payload: dict) -> dict``
            that returns at minimum ``{"video_path": str}``.
        manifest_base_dir: Override the manifest storage directory (useful in
            tests).
    """

    def __init__(
        self,
        tts_service: Any,
        video_service: Any,
        manifest_base_dir: str | None = None,
    ) -> None:
        self._tts = tts_service
        self._video = video_service
        self._manifest = ManifestService(base_dir=manifest_base_dir)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def rerender_scene(self, req: RerenderSceneRequest) -> Dict[str, Any]:
        """Execute the rerender flow for a single scene.

        Reads the stored manifest, regenerates the requested components
        (audio / video / both), updates the manifest at each step, and
        marks ``needs_reassembly = True`` so the caller knows to trigger
        a fresh FFmpeg assembly pass.

        Returns:
            A result dict with keys ``status``, ``project_id``,
            ``episode_id``, ``scene_id``, ``mode``, ``audio_result``,
            ``video_result``, and ``needs_reassembly``.
        """
        manifest = self._manifest.get_scene(
            req.project_id,
            req.episode_id,
            req.scene_id,
        )

        voiceover_text = req.override_voiceover_text or manifest.get("voiceover_text")
        duration_sec = req.override_duration_sec or manifest.get("duration_sec")

        if not voiceover_text:
            raise ValueError(
                f"Missing voiceover_text for scene '{req.scene_id}' "
                "(not in manifest and not provided via override_voiceover_text)"
            )
        if not duration_sec:
            raise ValueError(
                f"Missing duration_sec for scene '{req.scene_id}' "
                "(not in manifest and not provided via override_duration_sec)"
            )

        self._manifest.patch_scene(
            req.project_id,
            req.episode_id,
            req.scene_id,
            {
                "status": "rerendering",
                "rerender_started_at": datetime.utcnow().isoformat(),
                "rerender_mode": req.mode,
                "needs_reassembly": True,
            },
        )

        audio_result: Optional[Dict[str, Any]] = None
        video_result: Optional[Dict[str, Any]] = None

        try:
            if req.mode in ("audio", "both"):
                audio_result = self._rerender_audio(
                    manifest=manifest,
                    voiceover_text=voiceover_text,
                    duration_sec=duration_sec,
                )
                new_duration_sec = audio_result.get("duration_sec") or duration_sec
                self._manifest.patch_scene(
                    req.project_id,
                    req.episode_id,
                    req.scene_id,
                    {
                        "audio_path": audio_result.get("audio_url"),
                        "word_timings": audio_result.get("word_timings", []),
                        "duration_sec": new_duration_sec,
                        "previous_duration_sec": manifest.get("duration_sec"),
                    },
                )

            if req.mode in ("video", "both"):
                audio_path = (
                    audio_result.get("audio_url")
                    if audio_result
                    else manifest.get("audio_path")
                )
                if not audio_path:
                    raise ValueError(
                        f"No audio_path available for scene '{req.scene_id}'"
                        " — rerender audio first or provide an existing audio_path in the manifest."
                    )
                video_result = self._rerender_video(
                    manifest=manifest,
                    audio_path=audio_path,
                    duration_sec=duration_sec,
                )
                self._manifest.patch_scene(
                    req.project_id,
                    req.episode_id,
                    req.scene_id,
                    {
                        "video_path": video_result.get("video_path"),
                        "provider_payload": video_result.get("provider_payload", {}),
                    },
                )

            self._manifest.patch_scene(
                req.project_id,
                req.episode_id,
                req.scene_id,
                {
                    "status": "rerendered",
                    "rerender_finished_at": datetime.utcnow().isoformat(),
                    "needs_reassembly": True,
                    "needs_smart_reassembly": True,
                    "error": None,
                },
            )

            return {
                "status": "rerendered",
                "project_id": req.project_id,
                "episode_id": req.episode_id,
                "scene_id": req.scene_id,
                "mode": req.mode,
                "audio_result": audio_result,
                "video_result": video_result,
                "needs_reassembly": True,
            }

        except Exception as exc:
            self._manifest.patch_scene(
                req.project_id,
                req.episode_id,
                req.scene_id,
                {
                    "status": "rerender_failed",
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    },
                    "needs_reassembly": True,
                },
            )
            raise

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _rerender_audio(
        self,
        manifest: Dict[str, Any],
        voiceover_text: str,
        duration_sec: float,
    ) -> Dict[str, Any]:
        scene_payload = {
            "voiceover_text": voiceover_text,
            "duration_sec": duration_sec,
            "voice_directive": manifest.get(
                "voice_directive",
                {"tone": "documentary, calm", "speed": "normal", "pause": "normal", "stress_words": []},
            ),
        }
        tts_payload = build_tts_payload(scene_payload)
        return self._tts.generate(tts_payload)

    def _rerender_video(
        self,
        manifest: Dict[str, Any],
        audio_path: str,
        duration_sec: float,
    ) -> Dict[str, Any]:
        drama_metadata = manifest.get("drama_metadata", {})
        return self._video.render_scene({
            "scene_id": manifest["scene_id"],
            "duration_sec": duration_sec,
            "audio_url": audio_path,
            "render_purpose": manifest.get("render_purpose"),
            "emotion": drama_metadata.get("emotion"),
            "subtext": drama_metadata.get("subtext"),
            "intent": drama_metadata.get("intent"),
        })
