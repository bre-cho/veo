"""Centralised render path configuration.

Every render-pipeline module should resolve its default storage paths through
this module instead of hard-coding ``/data/renders/…`` or ``/tmp/…``.
Import ``render_paths`` (the singleton instance) and use its properties:

    from app.core.runtime_paths import render_paths

    manifest_dir = render_paths.manifests_dir
    chunks_dir   = render_paths.chunks_dir
    ...

All base roots come from :mod:`app.core.config` ``settings`` so they can be
overridden uniformly via environment variables (``RENDER_OUTPUT_DIR``,
``RENDER_CACHE_DIR``, ``STORAGE_ROOT``).
"""
from __future__ import annotations

import os
from pathlib import Path

from app.core.config import settings


class RenderPaths:
    """Resolves and exposes canonical filesystem paths for the render pipeline.

    Paths are derived from three roots in :class:`~app.core.config.Settings`:

    * ``render_output_dir``  (env ``RENDER_OUTPUT_DIR``) – final rendered
      artefacts: final MP4s, subtitle files, and per-scene chunks.
    * ``render_cache_dir``   (env ``RENDER_CACHE_DIR``)  – transient cached
      data: frame samples, detector results, concat scratch files.
    * ``storage_root``       (env ``STORAGE_ROOT``)      – primary storage
      hierarchy: manifests and dependency graphs.
    """

    # ------------------------------------------------------------------
    # Primary output tree (under render_output_dir)
    # ------------------------------------------------------------------

    @property
    def final_dir(self) -> str:
        """Root for final assembled episode MP4 files."""
        return os.path.join(settings.render_output_dir, "final")

    @property
    def chunks_dir(self) -> str:
        """Root for per-scene pre-encoded chunk MP4 files."""
        return os.path.join(settings.render_output_dir, "chunks")

    @property
    def subtitles_dir(self) -> str:
        """Root for episode-level ASS subtitle files."""
        return os.path.join(settings.render_output_dir, "subtitles")

    @property
    def scenes_dir(self) -> str:
        """Root for raw scene video files."""
        return os.path.join(settings.render_output_dir, "scenes")

    @property
    def audio_dir(self) -> str:
        """Root for raw scene audio files."""
        return os.path.join(settings.render_output_dir, "audio")

    # ------------------------------------------------------------------
    # Cache tree (under render_cache_dir)
    # ------------------------------------------------------------------

    @property
    def detector_cache_dir(self) -> str:
        """Persistent detector-result cache (frame hashes → detection JSON)."""
        return os.path.join(settings.render_cache_dir, "detector_cache")

    @property
    def frame_samples_dir(self) -> str:
        """Temporary JPEG frame samples extracted for subtitle placement."""
        return os.path.join(settings.render_cache_dir, "subtitle_frames")

    @property
    def concat_scratch_dir(self) -> str:
        """Directory for temporary FFmpeg concat-demuxer text files."""
        return os.path.join(settings.render_cache_dir, "concat_scratch")

    # ------------------------------------------------------------------
    # Storage tree (under storage_root)
    # ------------------------------------------------------------------

    @property
    def manifests_dir(self) -> str:
        """Root for per-scene JSON manifest files."""
        return os.path.join(settings.storage_root, "manifests")

    @property
    def dependency_dir(self) -> str:
        """Root for per-episode dependency graph JSON files."""
        return os.path.join(settings.storage_root, "dependency")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def scene_video_path(self, scene_id: str) -> str:
        """Canonical path for a scene's raw video file."""
        return os.path.join(self.scenes_dir, f"{scene_id}.mp4")

    def scene_audio_path(self, scene_id: str) -> str:
        """Canonical path for a scene's raw audio file."""
        return os.path.join(self.audio_dir, f"{scene_id}.wav")

    def episode_output_path(self, project_id: str, episode_id: str) -> str:
        """Canonical path for a fully assembled episode MP4."""
        out = Path(self.final_dir) / project_id
        out.mkdir(parents=True, exist_ok=True)
        return str(out / f"{episode_id}.mp4")

    def episode_subtitle_path(self, project_id: str, episode_id: str) -> str:
        """Canonical path for an episode's ASS subtitle file (assembly-level)."""
        out = Path(self.subtitles_dir) / project_id
        out.mkdir(parents=True, exist_ok=True)
        return str(out / f"{episode_id}.ass")

    def concat_scratch_path(self, project_id: str, episode_id: str) -> str:
        """Canonical path for a temporary FFmpeg concat-demuxer text file."""
        out = Path(self.concat_scratch_dir)
        out.mkdir(parents=True, exist_ok=True)
        return str(out / f"{project_id}_{episode_id}_concat.txt")

    def smart_concat_scratch_path(self, project_id: str, episode_id: str) -> str:
        """Canonical path for a smart-reassembly concat-demuxer text file."""
        out = Path(self.concat_scratch_dir)
        out.mkdir(parents=True, exist_ok=True)
        return str(out / f"{project_id}_{episode_id}_smart_concat.txt")


#: Singleton instance – import and use directly.
render_paths = RenderPaths()
