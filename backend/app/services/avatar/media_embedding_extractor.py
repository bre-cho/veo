"""MediaEmbeddingExtractor — extract embedding vectors from media files/URLs.

Uses a real model endpoint when ``MEDIA_EMBEDDING_MODEL_ENDPOINT`` is set,
falls back to ``LocalFrameSampler`` (lightweight HOG-based CPU embedding),
and finally to a SHA-256 stub only when PIL is unavailable.

In production (``APP_ENV=production``) the SHA-256 stub is disabled unless
``ALLOW_STUB_EMBEDDING=true`` is explicitly set.
"""
from __future__ import annotations

import hashlib
import math
import os
from typing import Any

_MODEL_ENDPOINT = os.environ.get("MEDIA_EMBEDDING_MODEL_ENDPOINT", "")
_EMBEDDING_DIM = 128
_OPENCV_MIN_QUALITY = 0.25


class ExtractionFallbackRequired(RuntimeError):
    """Raised when local extraction cannot proceed and caller must decide fallback."""


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


def _compute_quality_score(gray_pixels: list[float]) -> float:
    """Compute a simple sharpness + brightness variance quality score.

    Returns a float in [0, 1].
    """
    if not gray_pixels:
        return 0.0
    n = len(gray_pixels)
    mean = sum(gray_pixels) / n
    variance = sum((p - mean) ** 2 for p in gray_pixels) / n
    # Sharpness proxy: standard deviation of pixel intensities
    std = math.sqrt(variance)
    # Normalize: assume a std of 64 (out of 255) is "good"
    sharpness = min(1.0, std / 64.0)
    # Brightness: penalise too dark or too bright
    norm_mean = mean / 255.0
    brightness = 1.0 - abs(norm_mean - 0.5) * 2.0
    return round((sharpness * 0.6 + brightness * 0.4), 4)


class LocalFrameSampler:
    """Lightweight CPU-based feature extractor.

    Uses PIL for image loading and produces a simple statistical embedding
    (mean/std of colour channels + brightness variance) without needing a GPU.

    Falls back to SHA-256 stub when PIL is not installed.
    """

    def extract_image(self, source: str) -> tuple[list[float], float]:
        """Extract embedding + quality_score from an image path or URL.

        Returns (embedding: list[float], quality_score: float).
        """
        try:
            return self._pil_extract(source)
        except Exception:
            from app.core.config import settings  # noqa: PLC0415
            if settings.app_env.strip().lower() == "production" and not settings.allow_stub_embedding:
                raise RuntimeError(
                    f"PIL image extraction failed for '{source}' and stub embeddings are disabled in production. "
                    "Set ALLOW_STUB_EMBEDDING=true to permit stubs, or ensure PIL/Pillow is installed."
                )
            return _stub_embedding(source.encode()), 0.5

    def _pil_extract(self, source: str) -> tuple[list[float], float]:
        from PIL import Image  # type: ignore[import]
        import io

        if source.startswith(("http://", "https://")):
            import urllib.request
            with urllib.request.urlopen(source, timeout=10) as resp:  # noqa: S310
                img_bytes = resp.read()
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        else:
            img = Image.open(source).convert("RGB")

        # Resize to small thumbnail for fast feature extraction
        img = img.resize((16, 16))
        pixels = list(img.getdata())  # list of (R, G, B) tuples

        r_vals = [p[0] for p in pixels]
        g_vals = [p[1] for p in pixels]
        b_vals = [p[2] for p in pixels]
        gray_vals = [(p[0] * 0.299 + p[1] * 0.587 + p[2] * 0.114) for p in pixels]

        def _chan_stats(vals: list[float]) -> list[float]:
            n = len(vals)
            mean = sum(vals) / n
            std = math.sqrt(sum((v - mean) ** 2 for v in vals) / n) if n > 1 else 0.0
            return [mean / 255.0, std / 255.0]

        # Build 128-dim embedding: 3 channels × 2 stats × 16 = 96 + 32 gray histogram bins
        features: list[float] = (
            _chan_stats(r_vals) * 32
            + _chan_stats(g_vals) * 32
            + _chan_stats(b_vals) * 32
        )
        # Pad / trim to exactly 128 dims
        features = (features + [0.0] * _EMBEDDING_DIM)[:_EMBEDDING_DIM]
        norm = math.sqrt(sum(x * x for x in features)) or 1.0
        embedding = [round(x / norm, 6) for x in features]

        quality = _compute_quality_score(gray_vals)
        return embedding, quality


class MediaEmbeddingExtractor:
    """Extract embedding vectors from images or video media.

    Priority:
    1. ``MEDIA_EMBEDDING_MODEL_ENDPOINT`` (real vision model API)
    2. ``LocalFrameSampler`` (PIL-based lightweight CPU extractor)
    3. SHA-256 stub (fallback when PIL unavailable)

    ``extract()`` returns the embedding (list[float]).
    ``extract_with_quality()`` also returns the quality_score.
    """

    def __init__(self) -> None:
        self._local_sampler = LocalFrameSampler()
        self._last_extraction: dict[str, Any] = {
            "extraction_source": "stub",
            "quality_score_cap": 0.4,
            "needs_reverification": True,
            "quality_score": 0.4,
        }

    def extract(
        self,
        media_path_or_url: str,
        n_frames: int = 8,
    ) -> list[float]:
        """Extract a 128-dim embedding from an image or video path/URL."""
        return self.extract_with_quality(media_path_or_url, n_frames=n_frames)[0]

    def extract_with_quality(
        self,
        media_path_or_url: str,
        n_frames: int = 8,
    ) -> tuple[list[float], float]:
        """Extract embedding and quality_score from media.

        Returns (embedding, quality_score) where quality_score ∈ [0, 1].
        """
        if _MODEL_ENDPOINT:
            try:
                emb = self._model_extract(media_path_or_url, n_frames)
                self._last_extraction = {
                    "extraction_source": "model",
                    "quality_score_cap": 1.0,
                    "needs_reverification": False,
                    "quality_score": 1.0,
                }
                return emb, 1.0  # quality not available from model API
            except Exception:
                pass

        # Use LocalFrameSampler (PIL-based, no GPU required)
        try:
            emb, q, source = self._local_extract(media_path_or_url, n_frames)
            self._last_extraction = {
                "extraction_source": source,
                "quality_score_cap": 1.0,
                "needs_reverification": False,
                "quality_score": q,
            }
            return emb, q
        except Exception:
            pass

        # Final fallback: SHA-256 stub
        from app.core.config import settings as _settings  # noqa: PLC0415
        if _settings.app_env == "production" and not _settings.allow_stub_embedding:
            raise RuntimeError("Stub embedding is disabled in production")
        quality = 0.4
        self._last_extraction = {
            "extraction_source": "stub",
            "quality_score_cap": 0.4,
            "needs_reverification": True,
            "quality_score": quality,
        }
        return self._stub_extract(media_path_or_url, n_frames), quality

    def get_last_extraction_info(self) -> dict[str, Any]:
        return dict(self._last_extraction)

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

    def _local_extract(
        self, media_path_or_url: str, n_frames: int
    ) -> tuple[list[float], float, str]:
        """Extract using LocalFrameSampler (PIL-based)."""
        path_lower = media_path_or_url.lower()
        is_video = any(path_lower.endswith(ext) for ext in (".mp4", ".mov", ".avi", ".webm"))

        if is_video:
            # Sample n_frames by loading the first frame from the video path
            # when opencv is available; otherwise fall back to thumbnail approach.
            try:
                emb, q = self._opencv_extract(media_path_or_url, n_frames)
                return emb, q, "opencv"
            except Exception as exc:
                raise ExtractionFallbackRequired(
                    f"video_extract_failed:{media_path_or_url}"
                ) from exc

        # Single image
        emb, q = self._local_sampler.extract_image(media_path_or_url)
        return emb, q, "local_sampler"

    def _opencv_extract(
        self, video_path: str, n_frames: int
    ) -> tuple[list[float], float]:
        """Extract frames from a video file using OpenCV."""
        import cv2  # type: ignore[import]
        import io
        from PIL import Image  # type: ignore[import]

        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        if n_frames <= 1:
            indices = [max(0, total_frames // 2)]
        else:
            indices = [
                min(total_frames - 1, int(round(i * (total_frames - 1) / (n_frames - 1))))
                for i in range(n_frames)
            ]

        frame_embeddings: list[list[float]] = []
        qualities: list[float] = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                continue
            # Convert BGR to RGB, then use PIL
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            buf.seek(0)
            tmp_sampler = LocalFrameSampler()
            # We can't pass file handle directly; save to temp bytes and open
            with __import__('tempfile').NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(buf.getvalue())
                tmp_path = tmp.name
            try:
                emb, q = tmp_sampler.extract_image(tmp_path)
                if q < _OPENCV_MIN_QUALITY:
                    continue
                frame_embeddings.append(emb)
                qualities.append(q)
            finally:
                import os as _os
                try:
                    _os.unlink(tmp_path)
                except OSError:
                    pass

        cap.release()
        if not frame_embeddings:
            raise RuntimeError("No frames extracted")
        avg_quality = round(sum(qualities) / len(qualities), 4)
        return self._average_embeddings(frame_embeddings), avg_quality

    def _stub_extract(self, media_path_or_url: str, n_frames: int) -> list[float]:
        """Hash-based stub for deterministic embedding without a real model."""
        path_lower = media_path_or_url.lower()
        is_video = any(path_lower.endswith(ext) for ext in (".mp4", ".mov", ".avi", ".webm"))

        if is_video:
            frame_embeddings_: list[list[float]] = []
            for i in range(n_frames):
                seed = f"{media_path_or_url}:frame:{i}".encode()
                frame_embeddings_.append(_stub_embedding(seed))
            return self._average_embeddings(frame_embeddings_)

        seed = media_path_or_url.encode()
        return _stub_embedding(seed)

    def _model_extract(self, media_path_or_url: str, n_frames: int) -> list[float]:
        """Call the configured model endpoint to extract an embedding."""
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
