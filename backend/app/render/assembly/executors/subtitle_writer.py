from __future__ import annotations

from typing import List


def write_srt(subtitle_tracks: List[dict], output_path: str) -> str:
    """Write a plain SRT subtitle file from a list of subtitle track dicts.

    Args:
        subtitle_tracks: List of dicts with keys ``start_sec`` (float),
            ``end_sec`` (float), and ``text`` (str).
        output_path: Absolute path where the .srt file will be written.

    Returns:
        The ``output_path`` value passed in.
    """
    lines: List[str] = []

    for idx, sub in enumerate(subtitle_tracks, start=1):
        start = format_srt_time(sub["start_sec"])
        end = format_srt_time(sub["end_sec"])

        lines.extend([
            str(idx),
            f"{start} --> {end}",
            sub["text"],
            "",
        ])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_path


def format_srt_time(seconds: float) -> str:
    """Format a float number of seconds as an SRT timestamp ``HH:MM:SS,mmm``."""
    millis = int((seconds % 1) * 1000)
    secs = int(seconds)

    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60

    return f"{h:02}:{m:02}:{s:02},{millis:03}"
