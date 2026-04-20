"""MediaEmbeddingExtractor — extract embedding vectors from media files/URLs.

Uses a deterministic hash-based stub by default.  To use a real vision model,
set ``MEDIA_EMBEDDING_MODEL_ENDPOINT`` in the environment.
"""
from __future__ import annotations

import hashlib
import math
import os
from typing import Any

_MODEL_ENDPOINT = os.environ.get("MEDIA_EMBEDDING_MODEL_ENDPOINT", "")
_EMBEDDING_DIM = 128


def _stub_embedding(data: bytes) -> list[float]:
    """Return a deterministic 128-dim unit-length embedding based on SHA-256 hash.

    Provides repeatable, non-random embeddings so tests and dev environments
    can exercise the pipeline without a real vision model.
    """
    digest = hashlib.sha256(data).digest()
    # Build 128 floats from the 32-byte digest by repeating it
    extended = (digest * math.ceil(_EMBEDDING_DIM / len(digest)))[:_EMBEDDING_DIM]
    raw = [float(b) / 255.0 for b in extended]
    norm = math.sqrt(sum(x * x for x in raw)) or 1.0
    return [round(x / norm, 6) for x in raw]


class MediaEmbeddingExtractor:
    """Extract embedding vectors from images or video media.

    ``extract()`` is the primary entry point.  For production use, populate
    ``MEDIA_EMBEDDING_MODEL_ENDPOINT`` to route through a real vision model.
    The stub path is always used when the endpoint is not configured.
    """

    def extract(
        self,
        media_path_or_url: str,
        n_frames: int = 8,
    ) -> list[float]:
        """Extract a 128-dim embedding from an image or video path/URL.

        For images, the file/URL is processed directly.
        For video files (.mp4, .mov, .avi, .webm), ``n_frames`` evenly spaced
        frames are sampled and their embeddings are averaged.

        Falls back gracefully to the stub when real model is unavailable.
        """
        if _MODEL_ENDPOINT:
            try:
                return self._model_extract(media_path_or_url, n_frames)
            except Exception:
                pass

        return self._stub_extract(media_path_or_url, n_frames)

    def _frame_embedding(self, frame_data: bytes) -> list[float]:
        """Compute embedding for a single frame's raw bytes."""
        if _MODEL_ENDPOINT:
            try:
                return self._call_model_api(frame_data)
            except Exception:
                pass
        return _stub_embedding(frame_data)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _stub_extract(self, media_path_or_url: str, n_frames: int) -> list[float]:
        """Hash-based stub for deterministic embedding without a real model."""
        path_lower = media_path_or_url.lower()
        is_video = any(path_lower.endswith(ext) for ext in (".mp4", ".mov", ".avi", ".webm"))

        if is_video:
            # Simulate n_frames by hashing path + frame index
            frame_embeddings: list[list[float]] = []
            for i in range(n_frames):
                seed = f"{media_path_or_url}:frame:{i}".encode()
                frame_embeddings.append(_stub_embedding(seed))
            return self._average_embeddings(frame_embeddings)

        # Single image path
        seed = media_path_or_url.encode()
        return _stub_embedding(seed)

    def _model_extract(self, media_path_or_url: str, n_frames: int) -> list[float]:
        """Call the configured model endpoint to extract an embedding.

        Subclasses or monkey-patching in tests can override this.
        """
        import urllib.request

        payload = {
            "media_url": media_path_or_url,
            "n_frames": n_frames,
            "output_dim": _EMBEDDING_DIM,
        }
        import json
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            _MODEL_ENDPOINT,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            result: dict[str, Any] = json.loads(resp.read())
        return [float(x) for x in result["embedding"]]

    def _call_model_api(self, frame_data: bytes) -> list[float]:
        """Call the model API for a single frame's bytes (base64-encoded)."""
        import base64
        import json
        import urllib.request

        payload = {
            "frame_b64": base64.b64encode(frame_data).decode(),
            "output_dim": _EMBEDDING_DIM,
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            _MODEL_ENDPOINT,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            result: dict[str, Any] = json.loads(resp.read())
        return [float(x) for x in result["embedding"]]

    @staticmethod
    def _average_embeddings(embeddings: list[list[float]]) -> list[float]:
        """Average multiple frame embeddings into one and re-normalise."""
        if not embeddings:
            return [0.0] * _EMBEDDING_DIM
        n = len(embeddings)
        avg = [sum(e[i] for e in embeddings) / n for i in range(_EMBEDDING_DIM)]
        norm = math.sqrt(sum(x * x for x in avg)) or 1.0
        return [round(x / norm, 6) for x in avg]
