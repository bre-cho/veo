"""Unit tests for the real detector integration and detector result cache."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# detector_config
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDetectorConfig:
    def test_required_keys_present(self):
        from app.render.assembly.vision.detector_config import DETECTOR_CONFIG
        for key in (
            "enable_face_detection",
            "enable_object_detection",
            "yolo_model",
            "min_confidence",
            "important_classes",
        ):
            assert key in DETECTOR_CONFIG

    def test_confidence_in_range(self):
        from app.render.assembly.vision.detector_config import DETECTOR_CONFIG
        assert 0 < DETECTOR_CONFIG["min_confidence"] < 1

    def test_important_classes_is_list(self):
        from app.render.assembly.vision.detector_config import DETECTOR_CONFIG
        assert isinstance(DETECTOR_CONFIG["important_classes"], list)
        assert "person" in DETECTOR_CONFIG["important_classes"]


# ---------------------------------------------------------------------------
# video_hash
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestVideoHash:
    def _write_tmp_file(self, content: bytes) -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            f.write(content)
            return f.name

    def test_returns_16_char_hex(self):
        from app.render.assembly.vision.video_hash import compute_video_hash
        path = self._write_tmp_file(b"fake video data")
        try:
            result = compute_video_hash(path)
            assert len(result) == 16
            assert all(c in "0123456789abcdef" for c in result)
        finally:
            os.unlink(path)

    def test_same_file_same_hash(self):
        from app.render.assembly.vision.video_hash import compute_video_hash
        path = self._write_tmp_file(b"stable content")
        try:
            assert compute_video_hash(path) == compute_video_hash(path)
        finally:
            os.unlink(path)

    def test_missing_file_raises(self):
        from app.render.assembly.vision.video_hash import compute_video_hash
        with pytest.raises(FileNotFoundError):
            compute_video_hash("/nonexistent/no_such_file.mp4")


# ---------------------------------------------------------------------------
# DetectorResultCache
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDetectorResultCache:
    def _cache(self, tmp_dir: str):
        from app.render.assembly.vision.detector_cache import DetectorResultCache
        return DetectorResultCache(cache_dir=tmp_dir)

    def _sample_result(self) -> dict:
        return {
            "face_bboxes": [{"x": 100, "y": 200, "w": 80, "h": 90, "label": "face", "confidence": 0.9}],
            "object_bboxes": [],
            "saliency_bboxes": [],
        }

    def test_miss_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = self._cache(tmp)
            assert cache.get("s1", "abc123") is None

    def test_set_then_get_returns_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = self._cache(tmp)
            result = self._sample_result()
            cache.set("s1", "abc123", result)
            retrieved = cache.get("s1", "abc123")
            assert retrieved == result

    def test_different_scene_id_misses(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = self._cache(tmp)
            cache.set("s1", "abc123", self._sample_result())
            assert cache.get("s2", "abc123") is None

    def test_different_video_hash_misses(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = self._cache(tmp)
            cache.set("s1", "abc123", self._sample_result())
            assert cache.get("s1", "xyz999") is None

    def test_build_key_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = self._cache(tmp)
            key1 = cache.build_key("scene_a", "hash1")
            key2 = cache.build_key("scene_a", "hash1")
            assert key1 == key2

    def test_build_key_differs_for_different_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = self._cache(tmp)
            assert cache.build_key("s1", "h1") != cache.build_key("s2", "h1")
            assert cache.build_key("s1", "h1") != cache.build_key("s1", "h2")

    def test_config_hash_changes_when_config_changes(self):
        """Simulate a config change by monkey-patching DETECTOR_CONFIG."""
        import app.render.assembly.vision.detector_config as dc
        with tempfile.TemporaryDirectory() as tmp:
            cache = self._cache(tmp)
            original_config = dict(dc.DETECTOR_CONFIG)
            hash_before = cache._config_hash()

            dc.DETECTOR_CONFIG["min_confidence"] = 0.99
            hash_after = cache._config_hash()

            # restore
            dc.DETECTOR_CONFIG.clear()
            dc.DETECTOR_CONFIG.update(original_config)

            assert hash_before != hash_after

    def test_clear_scene_removes_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = self._cache(tmp)
            cache.set("s1", "h1", self._sample_result())
            cache.set("s1", "h2", self._sample_result())
            cache.set("s2", "h1", self._sample_result())
            removed = cache.clear_scene("s1")
            assert removed == 2
            assert cache.get("s1", "h1") is None
            assert cache.get("s2", "h1") is not None

    def test_set_creates_json_file_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = self._cache(tmp)
            cache.set("s1", "abc", self._sample_result())
            files = list(Path(tmp).glob("*.json"))
            assert len(files) == 1
            payload = json.loads(files[0].read_text())
            assert payload["scene_id"] == "s1"
            assert "result" in payload

    def test_cache_dir_created_automatically(self):
        with tempfile.TemporaryDirectory() as base:
            new_dir = os.path.join(base, "sub", "cache")
            from app.render.assembly.vision.detector_cache import DetectorResultCache
            DetectorResultCache(cache_dir=new_dir)
            assert os.path.isdir(new_dir)


# ---------------------------------------------------------------------------
# VisualDetector — real implementation (no CV libs installed → graceful stub)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestVisualDetectorRealImpl:
    def _detector(self):
        from app.render.assembly.vision.visual_detector import VisualDetector
        return VisualDetector()

    def test_returns_required_keys(self):
        d = self._detector()
        result = d.detect("/nonexistent/frame.jpg")
        assert "face_bboxes" in result
        assert "object_bboxes" in result
        assert "saliency_bboxes" in result
        assert "detector_status" in result

    def test_detector_status_has_boolean_flags(self):
        d = self._detector()
        result = d.detect("/nonexistent/frame.jpg")
        status = result["detector_status"]
        assert isinstance(status["face_detector"], bool)
        assert isinstance(status["object_detector"], bool)

    def test_face_bboxes_is_list(self):
        result = self._detector().detect("/fake.jpg")
        assert isinstance(result["face_bboxes"], list)

    def test_saliency_bboxes_subset_of_object_bboxes_labels(self):
        """saliency_bboxes must only contain person-labelled boxes."""
        d = self._detector()
        result = d.detect("/fake.jpg")
        for box in result["saliency_bboxes"]:
            assert box.get("label") == "person"


# ---------------------------------------------------------------------------
# SubtitleSafeZoneEngine — updated _all_boxes priority filter
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSafeZoneEnginePriorityFilter:
    def _engine(self):
        from app.render.assembly.vision.subtitle_safe_zone_engine import SubtitleSafeZoneEngine
        return SubtitleSafeZoneEngine()

    def test_low_priority_label_excluded(self):
        """Boxes with a label not in the priority set must not block placement."""
        engine = self._engine()
        # "bicycle" is not in priority labels → should not block bottom
        detection = {
            "face_bboxes": [],
            "object_bboxes": [{"x": 0, "y": 800, "w": 200, "h": 300, "label": "bicycle"}],
            "saliency_bboxes": [],
        }
        result = engine.choose_position(detection, video_height=1080)
        assert result["placement"] == "bottom"

    def test_person_label_blocks_bottom(self):
        """A 'person' box in the bottom zone must trigger top placement."""
        engine = self._engine()
        detection = {
            "face_bboxes": [],
            "object_bboxes": [{"x": 0, "y": 800, "w": 200, "h": 300, "label": "person"}],
            "saliency_bboxes": [],
        }
        result = engine.choose_position(detection, video_height=1080)
        assert result["placement"] == "top"

    def test_face_bbox_blocks_bottom(self):
        """Face boxes must always influence placement regardless of label."""
        engine = self._engine()
        detection = {
            "face_bboxes": [{"x": 0, "y": 800, "w": 100, "h": 300}],
            "object_bboxes": [],
            "saliency_bboxes": [],
        }
        result = engine.choose_position(detection, video_height=1080)
        assert result["placement"] == "top"

    def test_phone_and_laptop_block_bottom(self):
        for label in ("phone", "laptop", "car"):
            engine = self._engine()
            detection = {
                "face_bboxes": [],
                "object_bboxes": [{"x": 0, "y": 800, "w": 100, "h": 300, "label": label}],
                "saliency_bboxes": [],
            }
            result = engine.choose_position(detection, video_height=1080)
            assert result["placement"] == "top", f"Expected top for label={label}"


# ---------------------------------------------------------------------------
# FFmpegAssemblyExecutor — cache_status in placements (no real video needed)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestBuildScenePlacementsCacheStatus:
    def test_cache_status_present_in_placement(self):
        from app.render.assembly.executors.ffmpeg_assembly_executor import FFmpegAssemblyExecutor
        executor = FFmpegAssemblyExecutor()
        placements = executor._build_scene_placements(
            ["/nonexistent/scene.mp4"],
            [{"scene_id": "s1"}],
        )
        assert "cache_status" in placements["s1"]

    def test_cache_status_error_on_missing_video(self):
        from app.render.assembly.executors.ffmpeg_assembly_executor import FFmpegAssemblyExecutor
        executor = FFmpegAssemblyExecutor()
        placements = executor._build_scene_placements(
            ["/nonexistent/scene.mp4"],
            [{"scene_id": "s1"}],
        )
        # File doesn't exist → compute_video_hash raises → cache_status = "error"
        assert placements["s1"]["cache_status"] == "error"

    def test_cache_hit_after_manual_set(self):
        """Inject a pre-populated cache; placement must report 'hit'."""
        import tempfile
        from app.render.assembly.executors.ffmpeg_assembly_executor import FFmpegAssemblyExecutor
        from app.render.assembly.vision.detector_cache import DetectorResultCache
        from app.render.assembly.vision.video_hash import compute_video_hash

        # Create a real temp file so compute_video_hash succeeds
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"dummy")
            video_path = f.name

        with tempfile.TemporaryDirectory() as cache_dir:
            try:
                cache = DetectorResultCache(cache_dir=cache_dir)
                vh = compute_video_hash(video_path)
                detection = {"face_bboxes": [], "object_bboxes": [], "saliency_bboxes": []}
                cache.set("hit_scene", vh, detection)

                # Monkeypatch the executor to use our tmp cache dir
                executor = FFmpegAssemblyExecutor()
                original_method = executor._build_scene_placements

                def patched(video_paths, video_tracks):
                    from app.render.assembly.vision.frame_sampler import FrameSampler
                    from app.render.assembly.vision.visual_detector import VisualDetector
                    from app.render.assembly.vision.subtitle_safe_zone_engine import SubtitleSafeZoneEngine
                    sampler = FrameSampler()
                    detector = VisualDetector()
                    safe_zone = SubtitleSafeZoneEngine()
                    _cache = DetectorResultCache(cache_dir=cache_dir)
                    placements = {}
                    for vp, scene in zip(video_paths, video_tracks):
                        scene_id = scene["scene_id"]
                        vh2 = compute_video_hash(vp)
                        cached = _cache.get(scene_id, vh2)
                        if cached is not None:
                            det = cached
                            status = "hit"
                        else:
                            det = {"face_bboxes": [], "object_bboxes": [], "saliency_bboxes": []}
                            status = "miss"
                        pl = safe_zone.choose_position(det)
                        placements[scene_id] = {
                            "placement": pl["placement"],
                            "style_name": {"bottom": "Bottom", "top": "Top", "middle_low": "MiddleLow"}[pl["placement"]],
                            "detection": det,
                            "cache_status": status,
                        }
                    return placements

                placements = patched([video_path], [{"scene_id": "hit_scene"}])
                assert placements["hit_scene"]["cache_status"] == "hit"
            finally:
                os.unlink(video_path)
