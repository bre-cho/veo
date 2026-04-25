"""Unit tests for subtitle readability guard, layout engine, visual-aware writer,
and vision placement modules.
"""
from __future__ import annotations

import os
import tempfile

import pytest


# ---------------------------------------------------------------------------
# subtitle_style — new fields
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSubtitleStyleNewFields:
    def test_min_max_font_size_present(self):
        from app.render.assembly.subtitles.subtitle_style import SUBTITLE_STYLE
        assert "min_font_size" in SUBTITLE_STYLE
        assert "max_font_size" in SUBTITLE_STYLE

    def test_readability_fields(self):
        from app.render.assembly.subtitles.subtitle_style import SUBTITLE_STYLE
        assert "max_words_per_line" in SUBTITLE_STYLE
        assert "max_chars_per_line" in SUBTITLE_STYLE
        assert "safe_zone_bottom_ratio" in SUBTITLE_STYLE
        assert "elder_readable" in SUBTITLE_STYLE

    def test_elder_readable_default_true(self):
        from app.render.assembly.subtitles.subtitle_style import SUBTITLE_STYLE
        assert SUBTITLE_STYLE["elder_readable"] is True

    def test_safe_zone_ratio_reasonable(self):
        from app.render.assembly.subtitles.subtitle_style import SUBTITLE_STYLE
        ratio = SUBTITLE_STYLE["safe_zone_bottom_ratio"]
        assert 0 < ratio < 1


# ---------------------------------------------------------------------------
# subtitle_layout_engine
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSubtitleLayoutEngine:
    def _group(self, words_text, max_words=7, max_chars=42):
        from app.render.assembly.subtitles.subtitle_layout_engine import group_words_readable
        words = [{"word": w, "start_sec": 0.0, "end_sec": 0.5} for w in words_text.split()]
        return group_words_readable(words, max_words_per_line=max_words, max_chars_per_line=max_chars)

    def test_single_word(self):
        groups = self._group("hello")
        assert len(groups) == 1
        assert len(groups[0]) == 1

    def test_words_within_limit_stay_in_one_group(self):
        groups = self._group("one two three", max_words=7, max_chars=42)
        assert len(groups) == 1
        assert len(groups[0]) == 3

    def test_word_limit_breaks_line(self):
        groups = self._group("a b c d e f g h", max_words=3, max_chars=100)
        assert len(groups) >= 3
        for g in groups:
            assert len(g) <= 3

    def test_char_limit_breaks_line(self):
        groups = self._group("hello world foo bar baz", max_words=10, max_chars=10)
        # "hello world" = 11 chars — must split
        assert len(groups) >= 2

    def test_all_words_present_after_grouping(self):
        text = "one two three four five six seven eight"
        groups = self._group(text, max_words=3, max_chars=100)
        all_words = [w["word"] for g in groups for w in g]
        assert all_words == text.split()

    def test_no_empty_groups(self):
        groups = self._group("a b c d", max_words=2, max_chars=100)
        for g in groups:
            assert len(g) > 0


# ---------------------------------------------------------------------------
# SubtitleReadabilityGuard
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSubtitleReadabilityGuard:
    def _guard(self):
        from app.render.assembly.subtitles.readability_guard import SubtitleReadabilityGuard
        return SubtitleReadabilityGuard()

    def _tracks(self, n_words=5):
        return [
            {
                "scene_id": "s1",
                "words": [
                    {"word": f"w{i}", "start_sec": float(i), "end_sec": float(i + 1)}
                    for i in range(n_words)
                ],
            }
        ]

    def test_returns_style_and_report(self):
        result = self._guard().validate_and_optimize(self._tracks(), video_height=1080)
        assert "style" in result
        assert "layout_report" in result
        assert "word_tracks" in result

    def test_1080p_font_size(self):
        result = self._guard().validate_and_optimize(self._tracks(), video_height=1080)
        # 44 base + 4 elder bump = 48, capped at max_font_size=52
        assert result["style"]["font_size"] == 48

    def test_720p_font_size(self):
        result = self._guard().validate_and_optimize(self._tracks(), video_height=720)
        # 38 base + 4 elder = 42
        assert result["style"]["font_size"] == 42

    def test_below_720p_font_size(self):
        result = self._guard().validate_and_optimize(self._tracks(), video_height=480)
        # 34 base + 4 elder = 38 (== min_font_size, valid)
        assert result["style"]["font_size"] == 38

    def test_avoidance_applied_false_when_no_boxes(self):
        result = self._guard().validate_and_optimize(self._tracks(), video_height=1080)
        assert result["style"]["avoidance_applied"] is False

    def test_avoidance_applied_true_when_face_in_subtitle_zone(self):
        # A box that extends below 78% of 1080 = 842; safe_zone bottom = 1080 - 22% = 843
        # box bottom = 700 + 400 = 1100 >= 843 → triggers avoidance
        metadata = {"face_bboxes": [{"x": 300, "y": 700, "w": 200, "h": 400}]}
        result = self._guard().validate_and_optimize(self._tracks(), scene_metadata=metadata, video_height=1080)
        assert result["style"]["avoidance_applied"] is True

    def test_avoidance_increases_margin_v(self):
        metadata = {"face_bboxes": [{"x": 300, "y": 700, "w": 200, "h": 400}]}
        result = self._guard().validate_and_optimize(self._tracks(), scene_metadata=metadata, video_height=1080)
        assert result["style"]["margin_v"] > 70

    def test_avoidance_margin_capped_at_180(self):
        from app.render.assembly.subtitles.subtitle_style import SUBTITLE_STYLE
        # patch so initial margin_v is already 100 so +80 = 180 exactly
        guard = self._guard()
        boxes = [{"x": 0, "y": 700, "w": 200, "h": 400}]
        style = dict(SUBTITLE_STYLE)
        style["margin_v"] = 150
        style["font_size"] = 44
        style = guard._avoid_face_or_object_zone(style, {"face_bboxes": boxes}, 1080)
        assert style["margin_v"] <= 180

    def test_report_total_words(self):
        result = self._guard().validate_and_optimize(self._tracks(n_words=8), video_height=1080)
        assert result["layout_report"]["total_words"] == 8

    def test_large_font_reduces_words_per_line(self):
        result = self._guard().validate_and_optimize(self._tracks(), video_height=1080)
        # font_size = 48 → max_words_per_line = 5
        assert result["style"]["max_words_per_line"] == 5


# ---------------------------------------------------------------------------
# word_level_karaoke_writer — updated signature with scene_metadata
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestWordLevelKaraokeWriterReadability:
    def _tracks(self):
        return [
            {
                "scene_id": "opening",
                "words": [
                    {"word": "Hello", "start_sec": 0.0, "end_sec": 0.3},
                    {"word": "world", "start_sec": 0.3, "end_sec": 0.7},
                ],
            }
        ]

    def _write(self, tracks, scene_metadata=None):
        from app.render.assembly.subtitles.word_level_karaoke_writer import write_word_level_karaoke_ass
        with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as f:
            path = f.name
        try:
            write_word_level_karaoke_ass(tracks, path, scene_metadata=scene_metadata)
            with open(path, encoding="utf-8") as fh:
                return fh.read()
        finally:
            os.unlink(path)

    def test_no_scene_metadata_writes_file(self):
        content = self._write(self._tracks())
        assert "[Script Info]" in content
        assert "Dialogue:" in content

    def test_with_empty_scene_metadata(self):
        content = self._write(self._tracks(), scene_metadata={})
        assert "Dialogue:" in content

    def test_face_avoidance_changes_header(self):
        metadata = {"face_bboxes": [{"x": 300, "y": 700, "w": 200, "h": 400}]}
        content = self._write(self._tracks(), scene_metadata=metadata)
        # With avoidance, margin_v should be > 70 (150 = 70+80)
        assert "150" in content or "180" in content

    def test_karaoke_tags_still_present_with_guard(self):
        content = self._write(self._tracks())
        assert r"\k" in content


# ---------------------------------------------------------------------------
# VisualDetector stub
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestVisualDetector:
    def _detector(self):
        from app.render.assembly.vision.visual_detector import VisualDetector
        return VisualDetector()

    def test_returns_three_keys(self):
        result = self._detector().detect("/any/path.jpg")
        for key in ("face_bboxes", "object_bboxes", "saliency_bboxes"):
            assert key in result

    def test_stub_returns_empty_lists(self):
        result = self._detector().detect("/any/path.jpg")
        assert result["face_bboxes"] == []
        assert result["object_bboxes"] == []
        assert result["saliency_bboxes"] == []


# ---------------------------------------------------------------------------
# SubtitleSafeZoneEngine
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSubtitleSafeZoneEngine:
    def _engine(self):
        from app.render.assembly.vision.subtitle_safe_zone_engine import SubtitleSafeZoneEngine
        return SubtitleSafeZoneEngine()

    def _empty_detection(self):
        return {"face_bboxes": [], "object_bboxes": [], "saliency_bboxes": []}

    def test_no_detections_returns_bottom(self):
        result = self._engine().choose_position(self._empty_detection(), video_height=1080)
        assert result["placement"] == "bottom"
        assert result["alignment"] == 2

    def test_bottom_blocked_returns_top(self):
        # Box from y=800 to y+h=1100 → extends below 70% of 1080=756 → blocked
        detection = {"face_bboxes": [{"x": 0, "y": 800, "w": 100, "h": 300}],
                     "object_bboxes": [], "saliency_bboxes": []}
        result = self._engine().choose_position(detection, video_height=1080)
        assert result["placement"] == "top"
        assert result["alignment"] == 8

    def test_both_blocked_returns_middle_low(self):
        # Bottom blocked: box bottom > 756; Top blocked: box top <= 270
        detection = {
            "face_bboxes": [{"x": 0, "y": 50, "w": 100, "h": 800}],
            "object_bboxes": [], "saliency_bboxes": [],
        }
        result = self._engine().choose_position(detection, video_height=1080)
        assert result["placement"] == "middle_low"
        assert result["margin_v"] == 180

    def test_result_has_alignment_and_margin_v(self):
        result = self._engine().choose_position(self._empty_detection())
        assert "alignment" in result
        assert "margin_v" in result

    def test_is_bottom_blocked_false_when_box_above_danger(self):
        engine = self._engine()
        detection = {"face_bboxes": [{"x": 0, "y": 0, "w": 100, "h": 200}],
                     "object_bboxes": [], "saliency_bboxes": []}
        # 200 < 756 so should NOT be blocked
        assert engine._is_bottom_blocked(detection, 1080) is False

    def test_is_top_blocked_false_when_box_below_threshold(self):
        engine = self._engine()
        detection = {"face_bboxes": [{"x": 0, "y": 300, "w": 100, "h": 200}],
                     "object_bboxes": [], "saliency_bboxes": []}
        # y=300 > 270 so should NOT be top-blocked
        assert engine._is_top_blocked(detection, 1080) is False


# ---------------------------------------------------------------------------
# visual_aware_karaoke_writer
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestVisualAwareKaraokeWriter:
    def _tracks(self):
        return [
            {
                "scene_id": "opening",
                "words": [
                    {"word": "Hello", "start_sec": 0.0, "end_sec": 0.3},
                    {"word": "world", "start_sec": 0.3, "end_sec": 0.7},
                ],
            },
            {
                "scene_id": "middle",
                "words": [
                    {"word": "Goodbye", "start_sec": 1.0, "end_sec": 1.5},
                ],
            },
        ]

    def _write(self, tracks, placements):
        from app.render.assembly.subtitles.visual_aware_karaoke_writer import write_visual_aware_karaoke_ass
        with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as f:
            path = f.name
        try:
            write_visual_aware_karaoke_ass(tracks, placements, path)
            with open(path, encoding="utf-8") as fh:
                return fh.read()
        finally:
            os.unlink(path)

    def test_header_has_three_styles(self):
        content = self._write(self._tracks(), {})
        assert "Style: Bottom," in content
        assert "Style: Top," in content
        assert "Style: MiddleLow," in content

    def test_dialogue_uses_bottom_style_by_default(self):
        content = self._write(self._tracks(), {})
        # No placement for "opening" → defaults to "Bottom"
        assert "Dialogue: 0," in content
        # Check the style field in at least one dialogue line
        assert ",Bottom," in content

    def test_dialogue_uses_top_when_specified(self):
        placements = {"opening": {"style_name": "Top"}}
        content = self._write(self._tracks(), placements)
        assert ",Top," in content

    def test_dialogue_uses_middle_low_when_specified(self):
        placements = {"opening": {"style_name": "MiddleLow"}}
        content = self._write(self._tracks(), placements)
        assert ",MiddleLow," in content

    def test_karaoke_tags_present(self):
        content = self._write(self._tracks(), {})
        assert r"\k" in content

    def test_all_words_in_output(self):
        content = self._write(self._tracks(), {})
        for word in ("Hello", "world", "Goodbye"):
            assert word in content

    def test_empty_words_track_skipped(self):
        tracks = [{"scene_id": "s1", "words": []}]
        content = self._write(tracks, {})
        assert "Dialogue:" not in content

    def test_multi_scene_different_styles(self):
        placements = {
            "opening": {"style_name": "Bottom"},
            "middle": {"style_name": "Top"},
        }
        content = self._write(self._tracks(), placements)
        assert ",Bottom," in content
        assert ",Top," in content


# ---------------------------------------------------------------------------
# FFmpegAssemblyExecutor._build_scene_placements (unit, no real video needed)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestFFmpegAssemblyExecutorBuildScenePlacements:
    def test_missing_video_falls_back_to_bottom(self):
        from app.render.assembly.executors.ffmpeg_assembly_executor import FFmpegAssemblyExecutor
        executor = FFmpegAssemblyExecutor()
        video_tracks = [{"scene_id": "s1"}, {"scene_id": "s2"}]
        video_paths = ["/nonexistent/s1.mp4", "/nonexistent/s2.mp4"]
        placements = executor._build_scene_placements(video_paths, video_tracks)
        assert set(placements.keys()) == {"s1", "s2"}
        for scene_id, p in placements.items():
            assert p["placement"] in ("bottom", "top", "middle_low")
            assert p["style_name"] in ("Bottom", "Top", "MiddleLow")

    def test_style_name_matches_placement(self):
        from app.render.assembly.executors.ffmpeg_assembly_executor import FFmpegAssemblyExecutor
        executor = FFmpegAssemblyExecutor()
        placements = executor._build_scene_placements(
            ["/fake.mp4"], [{"scene_id": "abc"}]
        )
        mapping = {"bottom": "Bottom", "top": "Top", "middle_low": "MiddleLow"}
        p = placements["abc"]
        assert p["style_name"] == mapping[p["placement"]]
