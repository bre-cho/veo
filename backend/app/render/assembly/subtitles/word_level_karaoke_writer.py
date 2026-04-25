from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.render.assembly.subtitles.karaoke_subtitle_writer import format_ass_time
from app.render.assembly.subtitles.readability_guard import SubtitleReadabilityGuard
from app.render.assembly.subtitles.subtitle_layout_engine import group_words_readable


def write_word_level_karaoke_ass(
    word_tracks: List[dict],
    output_path: str,
    scene_metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Write an ASS subtitle file with true word-level karaoke timing.

    Before writing, runs :class:`SubtitleReadabilityGuard` to optimise font
    size, line limits, and subtitle position relative to any detected face or
    object bounding boxes in *scene_metadata*.

    Each word's ``\\k`` duration is derived from the actual TTS word
    timestamps, so the yellow highlight follows the voiceover precisely.

    Args:
        word_tracks: List of dicts, each with a ``scene_id`` key and a
            ``words`` list.  Every word entry must have ``word`` (str),
            ``start_sec`` (float), and ``end_sec`` (float).
        output_path: Destination path for the ``.ass`` file.
        scene_metadata: Optional dict with ``face_bboxes`` and/or
            ``object_bboxes`` lists used by the readability guard.

    Returns:
        The ``output_path`` value passed in.
    """
    guard = SubtitleReadabilityGuard()
    guarded = guard.validate_and_optimize(
        word_tracks=word_tracks,
        scene_metadata=scene_metadata,
    )

    style = guarded["style"]
    header = _build_ass_header(style)
    events: List[str] = []

    for track in word_tracks:
        words = track.get("words", [])
        if not words:
            continue

        for group in group_words_readable(
            words=words,
            max_words_per_line=style["max_words_per_line"],
            max_chars_per_line=style["max_chars_per_line"],
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
                f"Dialogue: 0,{start},{end},Default,,0,0,0,,{karaoke_text.strip()}"
            )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))

    return output_path


def _group_words(words: List[dict], max_words_per_line: int = 7) -> List[List[dict]]:
    """Legacy simple grouper (kept for backwards-compatibility).

    Prefer :func:`group_words_readable` for new callers.
    """
    return [
        words[i: i + max_words_per_line]
        for i in range(0, len(words), max_words_per_line)
    ]


def _build_ass_header(style: dict) -> str:
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
        f"Style: Default,{style['font_name']},{style['font_size']},"
        f"{style['primary_color']},{style['active_color']},{style['outline_color']},"
        f"{style['back_color']},1,0,0,0,100,100,0,0,1,"
        f"{style['outline']},{style['shadow']},{style['alignment']},80,80,{style['margin_v']},1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
