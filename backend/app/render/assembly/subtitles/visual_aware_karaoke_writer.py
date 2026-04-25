from __future__ import annotations

from typing import Any, Dict, List

from app.render.assembly.subtitles.karaoke_subtitle_writer import format_ass_time
from app.render.assembly.subtitles.subtitle_layout_engine import group_words_readable
from app.render.assembly.subtitles.subtitle_style import SUBTITLE_STYLE


def write_visual_aware_karaoke_ass(
    word_tracks: List[Dict[str, Any]],
    scene_placements: Dict[str, Dict[str, Any]],
    output_path: str,
) -> str:
    """Write a multi-style ASS subtitle file with per-scene visual placement.

    Three named styles are defined in the ASS header (``Bottom``, ``Top``,
    ``MiddleLow``).  Each Dialogue event references the style chosen for its
    scene by :class:`app.render.assembly.vision.subtitle_safe_zone_engine.SubtitleSafeZoneEngine`.

    Args:
        word_tracks: List of per-scene word-timing track dicts (``scene_id`` +
            ``words`` list with ``word``/``start_sec``/``end_sec`` keys).
        scene_placements: Mapping of ``scene_id`` → placement dict (must contain
            ``style_name`` which is one of ``"Bottom"``, ``"Top"``,
            ``"MiddleLow"``).
        output_path: Destination path for the ``.ass`` file.

    Returns:
        The ``output_path`` value passed in.
    """
    header = _build_ass_header()
    events: List[str] = []

    for track in word_tracks:
        scene_id = track["scene_id"]
        words = track.get("words", [])
        if not words:
            continue

        placement = scene_placements.get(scene_id, {})
        style_name = placement.get("style_name", "Bottom")

        for group in group_words_readable(
            words=words,
            max_words_per_line=SUBTITLE_STYLE["max_words_per_line"],
            max_chars_per_line=SUBTITLE_STYLE["max_chars_per_line"],
        ):
            start = format_ass_time(group[0]["start_sec"])
            end = format_ass_time(group[-1]["end_sec"])

            karaoke_text = ""
            for word in group:
                duration_cs = max(
                    int((word["end_sec"] - word["start_sec"]) * 100),
                    5,
                )
                karaoke_text += f"{{\\k{duration_cs}}}{word['word']} "

            events.append(
                f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{karaoke_text.strip()}"
            )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))

    return output_path


def _build_ass_header() -> str:
    s = SUBTITLE_STYLE
    common = (
        f"{s['font_name']},{s['font_size']},"
        f"{s['primary_color']},{s['active_color']},{s['outline_color']},"
        f"{s['back_color']},1,0,0,0,100,100,0,0,1,"
        f"{s['outline']},{s['shadow']}"
    )
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
        f"Style: Bottom,{common},2,80,80,70,1\n"
        f"Style: Top,{common},8,80,80,70,1\n"
        f"Style: MiddleLow,{common},2,80,80,180,1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
