from __future__ import annotations

from typing import List

from app.render.assembly.subtitles.subtitle_style import SUBTITLE_STYLE


def write_karaoke_ass(subtitle_tracks: List[dict], output_path: str) -> str:
    """Write an ASS subtitle file with per-word karaoke timing (equal distribution).

    Words within each subtitle chunk are highlighted in sequence, each for an
    equal fraction of the chunk duration.  This is the fallback path used when
    real word-level timestamps from TTS are unavailable.

    Args:
        subtitle_tracks: List of dicts with ``scene_id``, ``text``,
            ``start_sec``, and ``end_sec``.
        output_path: Destination path for the ``.ass`` file.

    Returns:
        The ``output_path`` value passed in.
    """
    header = _build_ass_header()
    events: List[str] = []

    for sub in subtitle_tracks:
        text = sub.get("text", "")
        words = text.split()
        if not words:
            continue

        start = format_ass_time(sub["start_sec"])
        end = format_ass_time(sub["end_sec"])

        duration_cs = int((sub["end_sec"] - sub["start_sec"]) * 100)
        per_word_cs = max(duration_cs // len(words), 10)

        karaoke_text = "".join(
            f"{{\\k{per_word_cs}}}{word} "
            for word in words
        )

        events.append(
            f"Dialogue: 0,{start},{end},Default,,0,0,0,,{karaoke_text.strip()}"
        )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))

    return output_path


def format_ass_time(seconds: float) -> str:
    """Format a float number of seconds as an ASS timestamp ``H:MM:SS.cc``."""
    cs = int((seconds % 1) * 100)
    secs = int(seconds)

    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60

    return f"{h}:{m:02}:{s:02}.{cs:02}"


def _build_ass_header() -> str:
    s = SUBTITLE_STYLE
    return (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1920\n"
        "PlayResY: 1080\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{s['font_name']},{s['font_size']},"
        f"{s['primary_color']},{s['active_color']},{s['outline_color']},"
        f"{s['back_color']},1,0,0,0,100,100,0,0,1,"
        f"{s['outline']},{s['shadow']},{s['alignment']},80,80,{s['margin_v']},1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
