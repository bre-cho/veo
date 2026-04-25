from __future__ import annotations

from pathlib import Path
from typing import List


class AssemblyValidator:
    """Validates that all required assets exist and the assembly plan is well-formed."""

    def validate_assets(self, video_paths: List[str], audio_paths: List[str]) -> None:
        """Raise FileNotFoundError if any expected asset file is absent.

        Args:
            video_paths: Absolute paths to scene video files.
            audio_paths: Absolute paths to scene audio files.

        Raises:
            FileNotFoundError: If one or more files do not exist on disk.
        """
        missing = [
            path for path in video_paths + audio_paths
            if not Path(path).exists()
        ]

        if missing:
            raise FileNotFoundError({
                "error": "Missing render assets",
                "missing": missing,
            })

    def validate_plan(self, assembly_plan: dict) -> None:
        """Raise ValueError if required top-level plan keys are absent or empty.

        Args:
            assembly_plan: The assembly plan dict produced by
                :class:`app.drama.timeline.engines.assembly_plan_engine`.

        Raises:
            ValueError: If ``video_tracks`` or ``audio_tracks`` are missing.
        """
        if not assembly_plan.get("video_tracks"):
            raise ValueError("assembly_plan.video_tracks is required")

        if not assembly_plan.get("audio_tracks"):
            raise ValueError("assembly_plan.audio_tracks is required")
