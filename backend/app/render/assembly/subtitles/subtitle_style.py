"""Visual style constants for ASS subtitle files.

Designed for maximum readability across all age groups:
- Large font so text is legible even on small screens / for older viewers
- White primary text with black outline so it reads over any background
- Yellow active (karaoke highlight) colour for real-time word tracking
- Bottom-centre placement with enough margin to avoid covering faces
"""
from __future__ import annotations

SUBTITLE_STYLE: dict = {
    "font_name": "Arial",
    "font_size": 44,
    "min_font_size": 38,
    "max_font_size": 52,

    "primary_color": "&H00FFFFFF",   # white
    "active_color": "&H0000FFFF",    # yellow (karaoke highlight)
    "outline_color": "&H00000000",   # black
    "back_color": "&H80000000",      # semi-transparent black box

    "outline": 3,
    "shadow": 1,

    "alignment": 2,                  # bottom-centre (ASS numpad alignment)
    "margin_v": 70,                  # pixels from bottom edge

    "max_words_per_line": 7,
    "max_chars_per_line": 42,

    "safe_zone_bottom_ratio": 0.22,  # subtitle starts at this fraction from bottom
    "elder_readable": True,          # bump font size +4 for accessibility
}
