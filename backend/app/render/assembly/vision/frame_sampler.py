from __future__ import annotations

import subprocess
from pathlib import Path


class FrameSampler:
    """Extracts a representative frame from a scene video for visual analysis.

    Uses FFmpeg to capture the frame at ``seek_sec`` seconds into the clip.
    The output JPEG is written to ``/tmp/subtitle_frames/{scene_id}.jpg``
    so that subsequent detectors can read it without re-running FFmpeg.
    """

    def sample_scene_frame(
        self,
        video_path: str,
        scene_id: str,
        seek_sec: str = "00:00:01",
    ) -> str:
        """Extract one frame from *video_path* and return its path.

        Args:
            video_path: Absolute path to the scene video file.
            scene_id: Used to name the output JPEG (avoids collisions).
            seek_sec: Seek position in ``HH:MM:SS`` format.  Defaults to
                one second in to avoid black/fade frames at the very start.

        Returns:
            Absolute path to the extracted JPEG frame.

        Raises:
            subprocess.CalledProcessError: If FFmpeg exits with a non-zero code.
        """
        out_dir = Path("/tmp/subtitle_frames")
        out_dir.mkdir(parents=True, exist_ok=True)

        frame_path = out_dir / f"{scene_id}.jpg"

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-ss", seek_sec,
            "-vframes", "1",
            str(frame_path),
        ]

        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)

        return str(frame_path)
