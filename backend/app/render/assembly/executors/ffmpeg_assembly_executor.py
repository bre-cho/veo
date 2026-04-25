from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from app.render.assembly.executors.asset_resolver import AssetResolver
from app.render.assembly.executors.assembly_validator import AssemblyValidator
from app.render.assembly.executors.ffmpeg_command_builder import FFmpegCommandBuilder
from app.render.assembly.subtitles.karaoke_subtitle_writer import write_karaoke_ass
from app.render.assembly.subtitles.visual_aware_karaoke_writer import write_visual_aware_karaoke_ass
from app.render.assembly.vision.detector_cache import DetectorResultCache
from app.render.assembly.vision.frame_sampler import FrameSampler
from app.render.assembly.vision.subtitle_safe_zone_engine import SubtitleSafeZoneEngine
from app.render.assembly.vision.video_hash import compute_video_hash
from app.render.assembly.vision.visual_detector import VisualDetector
from app.render.manifest.manifest_service import ManifestService

_logger = logging.getLogger(__name__)


class FFmpegAssemblyExecutor:
    """Executes the final FFmpeg assembly pass for a compiled episode timeline.

    Given an ``assembly_plan`` produced by
    :class:`app.drama.timeline.engines.assembly_plan_engine.build_assembly_plan`,
    this executor:

    1. Validates that the plan is well-formed.
    2. Resolves all scene video/audio asset paths.
    3. Validates that every asset exists on disk.
    4. Writes a karaoke ASS subtitle file (word-level if word timings are
       available, otherwise evenly distributed).
    5. Writes an FFmpeg concat demuxer file.
    6. Runs FFmpeg to concatenate videos, mix audio, burn subtitles, and
       encode the final MP4.
    """

    #: Maximum seconds FFmpeg is allowed to run for the full assembly pass.
    #: Override via the ``FFMPEG_ASSEMBLY_TIMEOUT_SEC`` environment variable.
    _DEFAULT_ASSEMBLY_TIMEOUT_SEC: int = 3600

    def __init__(self) -> None:
        import os as _os
        self.resolver = AssetResolver()
        self.validator = AssemblyValidator()
        self.builder = FFmpegCommandBuilder()
        self._manifest = ManifestService()
        self._assembly_timeout: int = int(
            _os.getenv("FFMPEG_ASSEMBLY_TIMEOUT_SEC", self._DEFAULT_ASSEMBLY_TIMEOUT_SEC)
        )

    def _build_scene_placements(
        self,
        video_paths: List[str],
        video_tracks: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """Sample one frame per scene and detect content to choose subtitle placement.

        For each scene, extracts a frame via FFmpeg, runs the stub visual
        detector, and asks :class:`SubtitleSafeZoneEngine` which of the three
        placement zones (bottom / top / middle_low) is safe.

        When the scene video file does not yet exist on disk (e.g. in tests or
        dry-run mode) the frame sampling step is skipped gracefully and the
        default ``bottom`` placement is used.

        Args:
            video_paths: Ordered list of resolved scene video paths.
            video_tracks: Corresponding list of video track dicts from the
                assembly plan (each must have a ``scene_id`` key).

        Returns:
            A mapping of ``scene_id`` → placement dict (``placement``,
            ``style_name``, ``detection``).
        """
        sampler = FrameSampler()
        detector = VisualDetector()
        safe_zone = SubtitleSafeZoneEngine()
        cache = DetectorResultCache()

        _STYLE_MAP: Dict[str, str] = {
            "bottom": "Bottom",
            "top": "Top",
            "middle_low": "MiddleLow",
        }

        placements: Dict[str, Dict[str, Any]] = {}

        for video_path, scene in zip(video_paths, video_tracks):
            scene_id = scene["scene_id"]

            try:
                video_hash = compute_video_hash(video_path)
                cached_result = cache.get(scene_id=scene_id, video_hash=video_hash)

                if cached_result is not None:
                    detection = cached_result
                    cache_status = "hit"
                else:
                    frame_path = sampler.sample_scene_frame(
                        video_path=video_path,
                        scene_id=scene_id,
                    )
                    detection = detector.detect(frame_path)
                    cache.set(scene_id=scene_id, video_hash=video_hash, result=detection)
                    cache_status = "miss"
            except Exception as exc:  # noqa: BLE001
                # Frame sampling / hashing can fail legitimately (video not yet on
                # disk during dry-runs, or no FFmpeg in the environment).  Fall back
                # to the safest default placement and log for diagnostics.
                _logger.warning(
                    "Frame sampling failed for scene %s (%s: %s); "
                    "defaulting to bottom placement.",
                    scene_id,
                    type(exc).__name__,
                    exc,
                )
                detection = {"face_bboxes": [], "object_bboxes": [], "saliency_bboxes": []}
                cache_status = "error"

            placement = safe_zone.choose_position(detection)

            placements[scene_id] = {
                "placement": placement["placement"],
                "style_name": _STYLE_MAP[placement["placement"]],
                "detection": detection,
                "cache_status": cache_status,
            }

        return placements

    def execute(
        self,
        project_id: str,
        episode_id: str,
        assembly_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run the full assembly pipeline for one episode.

        Args:
            project_id: Identifier for the owning project.
            episode_id: Identifier for the episode being assembled.
            assembly_plan: The plan dict from the Scene Timeline Compiler,
                containing ``video_tracks``, ``audio_tracks``,
                ``subtitle_tracks``, and optionally per-track ``word_timings``.

        Returns:
            A result dict with ``project_id``, ``episode_id``, ``status``,
            ``output_path``, ``subtitle_path``, and the ``command`` list.

        Raises:
            ValueError: If required plan keys are missing.
            FileNotFoundError: If expected scene assets are absent.
            RuntimeError: If the FFmpeg process exits with a non-zero code.
        """
        self.validator.validate_plan(assembly_plan)

        video_tracks: List[Dict[str, Any]] = assembly_plan["video_tracks"]
        audio_tracks: List[Dict[str, Any]] = assembly_plan["audio_tracks"]
        subtitle_tracks: List[Dict[str, Any]] = assembly_plan.get("subtitle_tracks", [])

        video_paths = [
            self.resolver.resolve_scene_video(scene["scene_id"])
            for scene in video_tracks
        ]
        audio_paths = [
            self.resolver.resolve_scene_audio(audio["scene_id"])
            for audio in audio_tracks
        ]

        self.validator.validate_assets(video_paths, audio_paths)

        output_path = self.resolver.resolve_output_path(project_id, episode_id)
        subtitle_path = self.resolver.resolve_subtitle_path(project_id, episode_id)

        # Choose word-level visual-aware karaoke if any audio track carries
        # word timings; otherwise fall back to evenly-distributed karaoke.
        word_tracks = [
            {"scene_id": audio["scene_id"], "words": audio["word_timings"]}
            for audio in audio_tracks
            if audio.get("word_timings")
        ]

        if word_tracks:
            scene_placements = self._build_scene_placements(video_paths, video_tracks)

            # Persist detection + placement to each scene's manifest.
            for scene in video_tracks:
                sid = scene["scene_id"]
                placement_data = scene_placements.get(sid, {})
                try:
                    self._manifest.patch_scene(
                        project_id=project_id,
                        episode_id=episode_id,
                        scene_id=sid,
                        patch={
                            "detection": placement_data.get("detection", {}),
                            "subtitle_placement": {
                                "placement": placement_data.get("placement"),
                                "style_name": placement_data.get("style_name"),
                                "cache_status": placement_data.get("cache_status"),
                            },
                        },
                    )
                except Exception as _exc:  # noqa: BLE001
                    _logger.warning("Failed to write manifest for scene %s: %s", sid, _exc)

            write_visual_aware_karaoke_ass(
                word_tracks=word_tracks,
                scene_placements=scene_placements,
                output_path=subtitle_path,
            )
        else:
            write_karaoke_ass(subtitle_tracks, subtitle_path)

        concat_file = f"/tmp/{project_id}_{episode_id}_concat.txt"
        self.builder.build_concat_file(video_paths=video_paths, concat_path=concat_file)

        command = self.builder.build_command(
            concat_file=concat_file,
            audio_paths=audio_paths,
            subtitle_path=subtitle_path,
            output_path=output_path,
        )

        result = subprocess.run(command, capture_output=True, text=True, timeout=self._assembly_timeout)

        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg assembly failed. stderr: {result.stderr}"
            )

        # Update every assembled scene's manifest with the final output paths.
        for scene in video_tracks:
            sid = scene["scene_id"]
            try:
                self._manifest.patch_scene(
                    project_id=project_id,
                    episode_id=episode_id,
                    scene_id=sid,
                    patch={
                        "subtitle_path": subtitle_path,
                        "final_output_path": output_path,
                        "status": "assembled",
                    },
                )
            except Exception as _exc:  # noqa: BLE001
                _logger.warning(
                    "Failed to write post-assembly manifest for scene %s: %s", sid, _exc
                )

        return {
            "project_id": project_id,
            "episode_id": episode_id,
            "status": "succeeded",
            "output_path": output_path,
            "subtitle_path": subtitle_path,
            "command": command,
        }
