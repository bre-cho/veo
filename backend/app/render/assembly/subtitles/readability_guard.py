from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.render.assembly.subtitles.subtitle_style import SUBTITLE_STYLE


class SubtitleReadabilityGuard:
    """Validates and optimises subtitle style for readability before burn-in.

    Adjusts font size, line length limits, and subtitle position to
    maximise legibility across different video resolutions, elder-readable
    mode, and when faces or important objects occupy the subtitle safe zone.
    """

    def validate_and_optimize(
        self,
        word_tracks: List[Dict[str, Any]],
        scene_metadata: Optional[Dict[str, Any]] = None,
        video_width: int = 1920,
        video_height: int = 1080,
    ) -> Dict[str, Any]:
        """Return an optimised style dict and a layout report.

        Args:
            word_tracks: Per-scene word-timing track list.
            scene_metadata: Optional dict with ``face_bboxes`` and/or
                ``object_bboxes`` lists (each box has ``x``, ``y``, ``w``, ``h``).
            video_width: Frame width in pixels (currently unused; reserved for
                future horizontal safe-zone checks).
            video_height: Frame height in pixels used for font-size selection
                and safe-zone calculations.

        Returns:
            A dict with keys:
            - ``style``: the resolved style dict to pass to the ASS header builder
            - ``word_tracks``: the original word_tracks (passed through unchanged)
            - ``layout_report``: a summary dict for logging / debugging
        """
        style = dict(SUBTITLE_STYLE)

        style = self._optimize_font_size(style, video_height)
        style = self._optimize_line_length(style)
        style = self._avoid_face_or_object_zone(
            style=style,
            scene_metadata=scene_metadata or {},
            video_height=video_height,
        )

        layout_report = self._build_report(style, word_tracks)

        return {
            "style": style,
            "word_tracks": word_tracks,
            "layout_report": layout_report,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _optimize_font_size(self, style: dict, video_height: int) -> dict:
        """Select base font size by resolution and bump for elder-readable mode."""
        if video_height >= 1080:
            style["font_size"] = 44
        elif video_height >= 720:
            style["font_size"] = 38
        else:
            style["font_size"] = 34

        if style.get("elder_readable"):
            style["font_size"] = min(
                style["font_size"] + 4,
                style["max_font_size"],
            )

        return style

    def _optimize_line_length(self, style: dict) -> dict:
        """Tighten words-per-line and chars-per-line limits for larger fonts."""
        font_size = style["font_size"]

        if font_size >= 48:
            style["max_words_per_line"] = 5
            style["max_chars_per_line"] = 34
        elif font_size >= 44:
            style["max_words_per_line"] = 6
            style["max_chars_per_line"] = 38
        else:
            style["max_words_per_line"] = 7
            style["max_chars_per_line"] = 42

        return style

    def _avoid_face_or_object_zone(
        self,
        style: dict,
        scene_metadata: dict,
        video_height: int,
    ) -> dict:
        """Raise margin and trim font if a detected box overlaps the subtitle zone.

        The subtitle zone's top-Y is estimated from ``safe_zone_bottom_ratio``.
        If any bounding box in ``face_bboxes`` or ``object_bboxes`` extends into
        that zone, ``margin_v`` is bumped by 80 px (capped at 180) and
        ``font_size`` is reduced by 2 (floored at ``min_font_size``).

        Args:
            style: Mutable style dict to update in place.
            scene_metadata: Dict with optional ``face_bboxes`` / ``object_bboxes``.
            video_height: Frame height in pixels.
        """
        danger_zones: list = (
            scene_metadata.get("face_bboxes", [])
            + scene_metadata.get("object_bboxes", [])
        )

        subtitle_top_y = video_height - int(
            video_height * style["safe_zone_bottom_ratio"]
        )

        for box in danger_zones:
            y = box.get("y", 0)
            h = box.get("h", 0)
            if y + h >= subtitle_top_y:
                style["margin_v"] = min(style["margin_v"] + 80, 180)
                style["font_size"] = max(
                    style["font_size"] - 2,
                    style["min_font_size"],
                )
                style["avoidance_applied"] = True
                return style

        style["avoidance_applied"] = False
        return style

    def _build_report(self, style: dict, word_tracks: List[dict]) -> dict:
        total_words = sum(len(track.get("words", [])) for track in word_tracks)

        return {
            "font_size": style["font_size"],
            "max_words_per_line": style["max_words_per_line"],
            "max_chars_per_line": style["max_chars_per_line"],
            "margin_v": style["margin_v"],
            "elder_readable": style.get("elder_readable", False),
            "avoidance_applied": style.get("avoidance_applied", False),
            "total_words": total_words,
        }
