"""Lightweight render path configuration — quick-verify safe.

Mirrors :mod:`app.core.runtime_paths` but uses :mod:`app.core.light_runtime_config`
(``os.getenv`` only) instead of :mod:`app.core.config` (pydantic + heavy deps).

This allows ``verify_unified_runtime.py --mode quick`` to import and exercise
all path resolution logic without touching the full Settings stack.

Every attribute name is identical to :class:`~app.core.runtime_paths.RenderPaths`
so that callers can switch between the two without changing attribute access.
"""
from __future__ import annotations

import os
from pathlib import Path

import app.core.light_runtime_config as _cfg


class LightRenderPaths:
    """Path resolver using lightweight env-only config (no pydantic, no DB)."""

    # ------------------------------------------------------------------
    # Primary output tree (under render_output_dir)
    # ------------------------------------------------------------------

    @property
    def final_dir(self) -> str:
        return os.path.join(_cfg.render_output_dir, "final")

    @property
    def chunks_dir(self) -> str:
        return os.path.join(_cfg.render_output_dir, "chunks")

    @property
    def subtitles_dir(self) -> str:
        return os.path.join(_cfg.render_output_dir, "subtitles")

    @property
    def scenes_dir(self) -> str:
        return os.path.join(_cfg.render_output_dir, "scenes")

    @property
    def audio_dir(self) -> str:
        return os.path.join(_cfg.render_output_dir, "audio")

    # ------------------------------------------------------------------
    # Cache tree (under render_cache_dir)
    # ------------------------------------------------------------------

    @property
    def detector_cache_dir(self) -> str:
        return os.path.join(_cfg.render_cache_dir, "detector_cache")

    @property
    def frame_samples_dir(self) -> str:
        return os.path.join(_cfg.render_cache_dir, "subtitle_frames")

    @property
    def concat_scratch_dir(self) -> str:
        return os.path.join(_cfg.render_cache_dir, "concat_scratch")

    # ------------------------------------------------------------------
    # Storage tree (under storage_root)
    # ------------------------------------------------------------------

    @property
    def manifests_dir(self) -> str:
        return os.path.join(_cfg.storage_root, "manifests")

    @property
    def dependency_dir(self) -> str:
        return os.path.join(_cfg.storage_root, "dependency")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def scene_video_path(self, scene_id: str) -> str:
        return os.path.join(self.scenes_dir, f"{scene_id}.mp4")

    def scene_audio_path(self, scene_id: str) -> str:
        return os.path.join(self.audio_dir, f"{scene_id}.wav")

    def episode_output_path(self, project_id: str, episode_id: str) -> str:
        out = Path(self.final_dir) / project_id
        out.mkdir(parents=True, exist_ok=True)
        return str(out / f"{episode_id}.mp4")

    def episode_subtitle_path(self, project_id: str, episode_id: str) -> str:
        out = Path(self.subtitles_dir) / project_id
        out.mkdir(parents=True, exist_ok=True)
        return str(out / f"{episode_id}.ass")

    def concat_scratch_path(self, project_id: str, episode_id: str) -> str:
        out = Path(self.concat_scratch_dir)
        out.mkdir(parents=True, exist_ok=True)
        return str(out / f"{project_id}_{episode_id}_concat.txt")

    def smart_concat_scratch_path(self, project_id: str, episode_id: str) -> str:
        out = Path(self.concat_scratch_dir)
        out.mkdir(parents=True, exist_ok=True)
        return str(out / f"{project_id}_{episode_id}_smart_concat.txt")


#: Singleton instance – import and use directly.
light_render_paths = LightRenderPaths()
