from __future__ import annotations

from typing import List

from app.render.assembly.subtitles.subtitle_style import SUBTITLE_STYLE
from app.render.assembly.subtitles.karaoke_subtitle_writer import format_ass_time


def write_word_level_karaoke_ass(
    word_tracks: List[dict],
    output_path: str,
) -> str:
    """Write an ASS subtitle file with true word-level karaoke timing.

    Each word's ``\\k`` duration is derived from the actual TTS word
    timestamps, so the yellow highlight follows the voiceover precisely
    rather than being evenly distributed.

    Args:
        word_tracks: List of dicts, each with a ``scene_id`` key and a
            ``words`` list.  Every word entry must have ``word`` (str),
            ``start_sec`` (float), and ``end_sec`` (float).
        output_path: Destination path for the ``.ass`` file.

    Returns:
        The ``output_path`` value passed in.
    """
    header = _build_ass_header()
    events: List[str] = []

    for track in word_tracks:
        words = track.get("words", [])
        if not words:
            continue

        for group in _group_words(words):
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
    """Split a flat word list into subtitle line groups of at most *max_words_per_line*."""
    return [
        words[i: i + max_words_per_line]
        for i in range(0, len(words), max_words_per_line)
    ]


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
