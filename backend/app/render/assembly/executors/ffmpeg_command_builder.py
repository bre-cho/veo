from __future__ import annotations

from pathlib import Path
from typing import List


class FFmpegCommandBuilder:
    """Builds FFmpeg concat + mix commands for final video assembly."""

    def build_concat_file(self, video_paths: List[str], concat_path: str) -> str:
        """Write an FFmpeg concat demuxer text file.

        Args:
            video_paths: Ordered list of absolute scene video paths.
            concat_path: Destination path for the concat file.

        Returns:
            The ``concat_path`` value passed in.
        """
        Path(concat_path).parent.mkdir(parents=True, exist_ok=True)

        with open(concat_path, "w", encoding="utf-8") as f:
            for path in video_paths:
                f.write(f"file '{path}'\n")

        return concat_path

    def build_command(
        self,
        concat_file: str,
        audio_paths: List[str],
        subtitle_path: str,
        output_path: str,
    ) -> List[str]:
        """Build the FFmpeg shell command list for final assembly.

        The command concatenates scene videos, mixes all scene audio tracks,
        burns in ASS subtitles, and encodes to H.264/AAC MP4.

        Args:
            concat_file: Path to the FFmpeg concat demuxer text file.
            audio_paths: Ordered list of per-scene audio WAV paths.
            subtitle_path: Path to the ASS subtitle file to burn in.
            output_path: Destination path for the final MP4.

        Returns:
            A list of strings forming the complete FFmpeg command.
        """
        command: List[str] = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
        ]

        for audio in audio_paths:
            command.extend(["-i", audio])

        audio_inputs = "".join(
            f"[{idx + 1}:a]"
            for idx in range(len(audio_paths))
        )

        filter_complex = (
            f"{audio_inputs}"
            f"concat=n={len(audio_paths)}:v=0:a=1[aout]"
        )

        command.extend([
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-vf", f"ass={subtitle_path}",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            "-shortest",
            output_path,
        ])

        return command
