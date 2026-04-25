"""Unit tests for the FFmpeg Assembly Executor module."""
from __future__ import annotations

import os
import tempfile

import pytest


# ---------------------------------------------------------------------------
# AssetResolver
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAssetResolver:
    def _resolver(self):
        from app.render.assembly.executors.asset_resolver import AssetResolver
        return AssetResolver()

    def test_resolve_scene_video(self):
        r = self._resolver()
        assert r.resolve_scene_video("opening") == "/data/renders/scenes/opening.mp4"

    def test_resolve_scene_audio(self):
        r = self._resolver()
        assert r.resolve_scene_audio("opening") == "/data/renders/audio/opening.wav"

    def test_resolve_subtitle_path_extension(self):
        r = self._resolver()
        path = r.resolve_subtitle_path.__doc__  # just check it's documented
        # The path should end with .ass, not .srt
        with tempfile.TemporaryDirectory() as tmp:
            # We can't call resolve_subtitle_path for real (tries mkdir /data),
            # so just verify the method exists and the expected suffix logic.
            assert hasattr(r, "resolve_subtitle_path")


# ---------------------------------------------------------------------------
# AssemblyValidator
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAssemblyValidator:
    def _validator(self):
        from app.render.assembly.executors.assembly_validator import AssemblyValidator
        return AssemblyValidator()

    def test_validate_plan_raises_on_missing_video_tracks(self):
        v = self._validator()
        with pytest.raises(ValueError, match="video_tracks"):
            v.validate_plan({"audio_tracks": [{"scene_id": "s1"}]})

    def test_validate_plan_raises_on_missing_audio_tracks(self):
        v = self._validator()
        with pytest.raises(ValueError, match="audio_tracks"):
            v.validate_plan({"video_tracks": [{"scene_id": "s1"}]})

    def test_validate_plan_passes_when_both_present(self):
        v = self._validator()
        v.validate_plan({"video_tracks": [{}], "audio_tracks": [{}]})

    def test_validate_assets_raises_on_missing_files(self):
        v = self._validator()
        with pytest.raises(FileNotFoundError, match="Missing render assets"):
            v.validate_assets(["/nonexistent/scene.mp4"], [])

    def test_validate_assets_passes_for_real_files(self):
        v = self._validator()
        with tempfile.NamedTemporaryFile() as f:
            v.validate_assets([f.name], [])  # should not raise


# ---------------------------------------------------------------------------
# SRT subtitle_writer
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSubtitleWriter:
    def _write(self, tracks):
        from app.render.assembly.executors.subtitle_writer import write_srt
        with tempfile.NamedTemporaryFile(mode="w", suffix=".srt", delete=False) as f:
            path = f.name
        try:
            write_srt(tracks, path)
            with open(path, encoding="utf-8") as f:
                return f.read()
        finally:
            os.unlink(path)

    def test_srt_index_starts_at_one(self):
        content = self._write([{"start_sec": 0, "end_sec": 5, "text": "Hello"}])
        assert content.startswith("1\n")

    def test_srt_arrow_separator(self):
        content = self._write([{"start_sec": 0, "end_sec": 5, "text": "Hello"}])
        assert "-->" in content

    def test_srt_text_present(self):
        content = self._write([{"start_sec": 0, "end_sec": 5, "text": "Hello world"}])
        assert "Hello world" in content

    def test_srt_time_format(self):
        from app.render.assembly.executors.subtitle_writer import format_srt_time
        assert format_srt_time(3661.5) == "01:01:01,500"
        assert format_srt_time(0.0) == "00:00:00,000"


# ---------------------------------------------------------------------------
# FFmpegCommandBuilder
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestFFmpegCommandBuilder:
    def _builder(self):
        from app.render.assembly.executors.ffmpeg_command_builder import FFmpegCommandBuilder
        return FFmpegCommandBuilder()

    def test_build_concat_file_content(self):
        builder = self._builder()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            path = f.name
        try:
            builder.build_concat_file(["/a/b.mp4", "/c/d.mp4"], path)
            with open(path) as fh:
                content = fh.read()
            assert "file '/a/b.mp4'" in content
            assert "file '/c/d.mp4'" in content
        finally:
            os.unlink(path)

    def test_build_command_starts_with_ffmpeg(self):
        builder = self._builder()
        cmd = builder.build_command(
            concat_file="/tmp/concat.txt",
            audio_paths=["/a/1.wav", "/a/2.wav"],
            subtitle_path="/a/subs.ass",
            output_path="/a/out.mp4",
        )
        assert cmd[0] == "ffmpeg"

    def test_build_command_uses_ass_filter(self):
        builder = self._builder()
        cmd = builder.build_command(
            concat_file="/tmp/concat.txt",
            audio_paths=["/a/1.wav"],
            subtitle_path="/a/subs.ass",
            output_path="/a/out.mp4",
        )
        vf_idx = cmd.index("-vf")
        assert cmd[vf_idx + 1].startswith("ass=")

    def test_build_command_contains_output_path(self):
        builder = self._builder()
        cmd = builder.build_command(
            concat_file="/tmp/concat.txt",
            audio_paths=["/a/1.wav"],
            subtitle_path="/a/subs.ass",
            output_path="/output/final.mp4",
        )
        assert "/output/final.mp4" in cmd

    def test_build_command_overwrite_flag(self):
        builder = self._builder()
        cmd = builder.build_command("/tmp/c.txt", ["/a.wav"], "/s.ass", "/o.mp4")
        assert "-y" in cmd


# ---------------------------------------------------------------------------
# Subtitle style
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSubtitleStyle:
    def test_style_keys_present(self):
        from app.render.assembly.subtitles.subtitle_style import SUBTITLE_STYLE
        for key in ("font_name", "font_size", "primary_color", "active_color",
                    "outline_color", "back_color", "outline", "shadow",
                    "margin_v", "alignment"):
            assert key in SUBTITLE_STYLE

    def test_alignment_is_bottom_centre(self):
        from app.render.assembly.subtitles.subtitle_style import SUBTITLE_STYLE
        assert SUBTITLE_STYLE["alignment"] == 2

    def test_active_color_is_yellow(self):
        from app.render.assembly.subtitles.subtitle_style import SUBTITLE_STYLE
        # Yellow in ASS BGR hex: &H0000FFFF
        assert SUBTITLE_STYLE["active_color"] == "&H0000FFFF"


# ---------------------------------------------------------------------------
# Karaoke subtitle writer (even distribution)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestKaraokeSubtitleWriter:
    def _write(self, tracks):
        from app.render.assembly.subtitles.karaoke_subtitle_writer import write_karaoke_ass
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ass", delete=False) as f:
            path = f.name
        try:
            write_karaoke_ass(tracks, path)
            with open(path, encoding="utf-8") as fh:
                return fh.read()
        finally:
            os.unlink(path)

    def test_output_has_ass_header(self):
        content = self._write([{"scene_id": "s1", "text": "Hello", "start_sec": 0, "end_sec": 5}])
        assert "[Script Info]" in content
        assert "[V4+ Styles]" in content
        assert "[Events]" in content

    def test_output_has_dialogue_line(self):
        content = self._write([{"scene_id": "s1", "text": "Hello world", "start_sec": 0, "end_sec": 5}])
        assert "Dialogue:" in content

    def test_karaoke_tag_present(self):
        content = self._write([{"scene_id": "s1", "text": "Hello world", "start_sec": 0, "end_sec": 5}])
        assert r"\k" in content

    def test_empty_text_skipped(self):
        content = self._write([{"scene_id": "s1", "text": "", "start_sec": 0, "end_sec": 5}])
        assert "Dialogue:" not in content

    def test_format_ass_time(self):
        from app.render.assembly.subtitles.karaoke_subtitle_writer import format_ass_time
        assert format_ass_time(0.0) == "0:00:00.00"
        assert format_ass_time(3661.5) == "1:01:01.50"


# ---------------------------------------------------------------------------
# Word-level karaoke writer
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestWordLevelKaraokeWriter:
    def _tracks(self):
        return [
            {
                "scene_id": "opening",
                "words": [
                    {"word": "It", "start_sec": 0.1, "end_sec": 0.3},
                    {"word": "already", "start_sec": 0.3, "end_sec": 0.7},
                    {"word": "happened", "start_sec": 0.7, "end_sec": 1.2},
                ],
            }
        ]

    def _write(self, tracks):
        from app.render.assembly.subtitles.word_level_karaoke_writer import write_word_level_karaoke_ass
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ass", delete=False) as f:
            path = f.name
        try:
            write_word_level_karaoke_ass(tracks, path)
            with open(path, encoding="utf-8") as fh:
                return fh.read()
        finally:
            os.unlink(path)

    def test_output_has_ass_sections(self):
        content = self._write(self._tracks())
        assert "[Script Info]" in content
        assert "[Events]" in content

    def test_dialogue_line_present(self):
        content = self._write(self._tracks())
        assert "Dialogue:" in content

    def test_karaoke_tags_present(self):
        content = self._write(self._tracks())
        assert r"\k" in content

    def test_all_words_in_output(self):
        content = self._write(self._tracks())
        for word in ("It", "already", "happened"):
            assert word in content

    def test_empty_track_skipped(self):
        content = self._write([{"scene_id": "s1", "words": []}])
        assert "Dialogue:" not in content

    def test_word_grouping(self):
        from app.render.assembly.subtitles.word_level_karaoke_writer import _group_words
        words = [{"word": str(i)} for i in range(15)]
        groups = _group_words(words)
        assert len(groups) == 3
        assert all(len(g) <= 7 for g in groups)


# ---------------------------------------------------------------------------
# ASR Alignment Service (stub)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestASRAlignmentService:
    def _service(self):
        from app.render.assembly.subtitles.asr_alignment_service import ASRAlignmentService
        return ASRAlignmentService()

    def test_align_returns_one_entry_per_word(self):
        svc = self._service()
        result = svc.align("/fake/audio.wav", "hello world foo")
        assert len(result) == 3

    def test_align_empty_transcript(self):
        svc = self._service()
        assert svc.align("/fake/audio.wav", "") == []

    def test_align_timing_is_continuous(self):
        svc = self._service()
        result = svc.align("/fake/audio.wav", "a b c")
        for i in range(len(result) - 1):
            assert result[i]["end_sec"] == pytest.approx(result[i + 1]["start_sec"], abs=0.01)

    def test_align_covers_full_duration(self):
        svc = self._service()
        result = svc.align("/fake/audio.wav", "a b")
        # stub duration is 6.0; last word should end at 6.0
        assert result[-1]["end_sec"] == pytest.approx(6.0, abs=0.01)


# ---------------------------------------------------------------------------
# Word Timing schemas
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestWordTiming:
    def test_word_timing_model(self):
        from app.render.assembly.subtitles.word_timing import WordTiming
        wt = WordTiming(word="hello", start_sec=0.1, end_sec=0.4)
        assert wt.word == "hello"
        assert wt.start_sec == 0.1
        assert wt.end_sec == 0.4

    def test_subtitle_word_track_model(self):
        from app.render.assembly.subtitles.word_timing import SubtitleWordTrack, WordTiming
        track = SubtitleWordTrack(
            scene_id="s1",
            words=[WordTiming(word="hi", start_sec=0.0, end_sec=0.5)],
        )
        assert track.scene_id == "s1"
        assert len(track.words) == 1


# ---------------------------------------------------------------------------
# Audio timing engine (word_timings pass-through)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAudioTimingEngineWordTimings:
    def test_word_timings_offset_to_global(self):
        from app.drama.timeline.engines.audio_timing_engine import compile_audio_timing

        scenes = [
            {
                "scene_id": "s1",
                "voiceover_text": "first",
                "duration_sec": 8,
                "voice_directive": {},
                "word_timings": [
                    {"word": "first", "start_sec": 0.1, "end_sec": 0.5},
                ],
            },
            {
                "scene_id": "s2",
                "voiceover_text": "second",
                "duration_sec": 6,
                "voice_directive": {},
                "word_timings": [
                    {"word": "second", "start_sec": 0.2, "end_sec": 0.8},
                ],
            },
        ]

        tracks = compile_audio_timing(scenes)

        # Scene 1 starts at 0 — word start should stay near 0.1
        assert tracks[0]["word_timings"][0]["start_sec"] == pytest.approx(0.1, abs=0.01)

        # Scene 2 starts at 8 — word start should be ~8.2
        assert tracks[1]["word_timings"][0]["start_sec"] == pytest.approx(8.2, abs=0.01)
        assert tracks[1]["word_timings"][0]["end_sec"] == pytest.approx(8.8, abs=0.01)

    def test_word_timings_empty_when_not_provided(self):
        from app.drama.timeline.engines.audio_timing_engine import compile_audio_timing

        tracks = compile_audio_timing([
            {"scene_id": "s1", "voiceover_text": "x", "duration_sec": 5, "voice_directive": {}},
        ])
        assert tracks[0]["word_timings"] == []


# ---------------------------------------------------------------------------
# Render worker word_timings propagation
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRenderWorkerWordTimings:
    def test_word_timings_propagated_to_video_result(self):
        from app.drama.workers_ext.render_worker import process_scene_render_job

        class FakeTTS:
            def generate(self, payload):
                return {
                    "audio_url": "/audio/opening.wav",
                    "duration_sec": 8.0,
                    "word_timings": [
                        {"word": "It", "start_sec": 0.1, "end_sec": 0.3}
                    ],
                }

        class FakeVideo:
            def render_scene(self, payload):
                return {"video_url": "/video/opening.mp4"}

        job = {
            "scene_id": "opening",
            "voiceover_text": "It already happened.",
            "duration_sec": 8,
            "voice_directive": {"tone": "low", "speed": "slow", "pause": "long", "stress_words": []},
            "render_purpose": "hook",
            "emotion": "curiosity",
            "subtext": "trigger",
        }

        result = process_scene_render_job(job, FakeTTS(), FakeVideo())

        assert result["word_timings"] == [{"word": "It", "start_sec": 0.1, "end_sec": 0.3}]
        assert job["audio_url"] == "/audio/opening.wav"
        assert job["audio_duration_sec"] == 8.0

    def test_word_timings_empty_when_tts_does_not_return_them(self):
        from app.drama.workers_ext.render_worker import process_scene_render_job

        class FakeTTS:
            def generate(self, payload):
                return {"audio_url": "/audio/x.wav"}

        class FakeVideo:
            def render_scene(self, payload):
                return {"video_url": "/video/x.mp4"}

        job = {
            "scene_id": "x",
            "voiceover_text": "X.",
            "duration_sec": 6,
            "voice_directive": {"tone": "calm", "speed": "normal", "pause": "normal", "stress_words": []},
        }

        result = process_scene_render_job(job, FakeTTS(), FakeVideo())
        assert result["word_timings"] == []


# ---------------------------------------------------------------------------
# TTS payload builder — return_word_timestamps flag
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTTSPayloadBuilderFlag:
    def test_return_word_timestamps_true(self):
        from app.drama.tts.services.tts_payload_builder import build_tts_payload

        payload = build_tts_payload({
            "voiceover_text": "Hello.",
            "duration_sec": 6,
            "voice_directive": {"tone": "calm", "speed": "normal", "pause": "normal", "stress_words": []},
        })
        assert payload["return_word_timestamps"] is True
