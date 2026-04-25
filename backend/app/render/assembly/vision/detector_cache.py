from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

from app.render.assembly.vision.detector_config import DETECTOR_CONFIG


class DetectorResultCache:
    """Persists detector results as JSON files to avoid re-running MediaPipe/YOLO.

    Cache keys incorporate ``scene_id``, a hash of the video file's metadata
    (path + size + mtime via :func:`video_hash.compute_video_hash`), and a
    hash of ``DETECTOR_CONFIG`` so that changing the detector configuration
    automatically invalidates all stored results.

    The cache directory defaults to ``/tmp/detector_cache`` and is created
    automatically.  Override *cache_dir* in tests to use a temporary directory.
    """

    def __init__(self, cache_dir: str = "/tmp/detector_cache") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_key(self, scene_id: str, video_hash: str) -> str:
        """Return the full SHA-256 hex cache key for a scene + video combination.

        The key changes whenever ``scene_id``, ``video_hash``, or
        ``DETECTOR_CONFIG`` changes.
        """
        raw = f"{scene_id}:{video_hash}:{self._config_hash()}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def get(self, scene_id: str, video_hash: str) -> Optional[Dict[str, Any]]:
        """Return the cached detection result, or *None* on a cache miss.

        Args:
            scene_id: Scene identifier used when the result was stored.
            video_hash: Hash produced by
                :func:`app.render.assembly.vision.video_hash.compute_video_hash`.

        Returns:
            The ``result`` dict that was passed to :meth:`set`, or ``None`` if
            no matching cache entry exists.
        """
        path = self.cache_dir / f"{self.build_key(scene_id, video_hash)}.json"
        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        return payload.get("result")

    def set(
        self,
        scene_id: str,
        video_hash: str,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Persist *result* to disk and return the full cache payload.

        Args:
            scene_id: Scene identifier.
            video_hash: Hash of the video file.
            result: Detection result dict returned by
                :meth:`app.render.assembly.vision.visual_detector.VisualDetector.detect`.

        Returns:
            The full payload dict written to disk (useful for debugging).
        """
        key = self.build_key(scene_id, video_hash)
        path = self.cache_dir / f"{key}.json"

        payload = {
            "scene_id": scene_id,
            "video_hash": video_hash,
            "detector_config_hash": self._config_hash(),
            "result": result,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        return payload

    def clear_scene(self, scene_id: str) -> int:
        """Remove all cache entries for *scene_id* regardless of video hash.

        Useful for manual invalidation when a scene is completely re-rendered.

        Args:
            scene_id: The scene identifier to purge.

        Returns:
            The number of cache files removed.
        """
        removed = 0
        for path in self.cache_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                if payload.get("scene_id") == scene_id:
                    path.unlink()
                    removed += 1
            except Exception:  # noqa: BLE001
                # Corrupt / unreadable cache entry — skip silently
                pass
        return removed

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _config_hash(self) -> str:
        """Return a 16-char hex digest of the current ``DETECTOR_CONFIG``."""
        raw = json.dumps(
            DETECTOR_CONFIG,
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]
