from __future__ import annotations

import logging
import math
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.autovis import AvatarDna, AvatarMotionDna, AvatarVisualDna, AvatarVoiceDna
from app.repositories.avatar_repo import AvatarRepo

logger = logging.getLogger(__name__)
_repo = AvatarRepo()

# ---------------------------------------------------------------------------
# Identity gate threshold for post-render verification
# ---------------------------------------------------------------------------
IDENTITY_GATE_THRESHOLD = 0.80
_TEMPORAL_CONTINUITY_THRESHOLD = 0.90


class IdentityDriftException(Exception):
    """Raised when a render output fails the identity gate check."""

    def __init__(self, avatar_id: str, similarity: float) -> None:
        self.avatar_id = avatar_id
        self.similarity = similarity
        super().__init__(
            f"Identity drift detected for avatar '{avatar_id}': "
            f"similarity={similarity:.3f} < threshold={IDENTITY_GATE_THRESHOLD}"
        )

# ---------------------------------------------------------------------------
# Consistency scoring thresholds
# ---------------------------------------------------------------------------
_FACE_SIMILARITY_FIELDS = ("skin_tone", "eye_color", "age_range", "gender_expression")
_STYLE_SIMILARITY_FIELDS = ("hair_style", "hair_color", "outfit_code", "background_code")
_MOTION_CONSISTENCY_FIELDS = ("motion_style", "gesture_set", "lipsync_mode")

# Drift thresholds — output is flagged/rejected when similarity drops below this
_FACE_DRIFT_THRESHOLD = 0.65
_STYLE_DRIFT_THRESHOLD = 0.60
_MOTION_DRIFT_THRESHOLD = 0.55
# Cosine similarity threshold for embedding-based consistency check
_EMBEDDING_DRIFT_THRESHOLD = 0.80
# Threshold below which a render is flagged for identity review
_RENDER_CONSISTENCY_THRESHOLD = 0.70


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return round(dot / (norm_a * norm_b), 6)


class AvatarEmbeddingStore:
    """Manages embedding vectors for avatar identity comparison.

    When a ``AvatarVisualDna.embedding_vector`` is populated, cosine similarity
    is used instead of (or alongside) field-level matching for more robust
    identity checks.
    """

    def get_embedding(self, db: Session, avatar_id: str) -> list[float] | None:
        visual: AvatarVisualDna | None = _repo.get_visual(db, avatar_id)
        if visual is None:
            return None
        vec = visual.embedding_vector
        if not isinstance(vec, list):
            return None
        return [float(v) for v in vec]

    def set_embedding(
        self,
        db: Session,
        avatar_id: str,
        embedding: list[float],
    ) -> AvatarVisualDna:
        return _repo.upsert_visual(db, avatar_id, {"embedding_vector": embedding})

    def similarity(
        self,
        db: Session,
        avatar_id: str,
        candidate_embedding: list[float],
    ) -> float:
        """Return cosine similarity between the avatar's canonical embedding and a candidate."""
        ref = self.get_embedding(db, avatar_id)
        if ref is None:
            return 1.0  # No reference → treat as consistent
        return _cosine_similarity(ref, candidate_embedding)


class AvatarConsistencyGuard:
    """Frame-level identity drift detection.

    ``lock_frame_sequence()`` compares each frame embedding against the avatar's
    canonical reference and returns a per-frame drift score list.
    """

    def __init__(self) -> None:
        self._embedding_store = AvatarEmbeddingStore()

    def lock_frame_sequence(
        self,
        db: Session,
        avatar_id: str,
        frame_embeddings: list[list[float]],
    ) -> list[dict[str, Any]]:
        """Score each frame against the avatar's canonical embedding.

        Returns a list of per-frame dicts with:
        - ``frame_index``: 0-based index
        - ``cosine_similarity``: float in [0, 1]
        - ``drift_detected``: bool (True when similarity < threshold)
        """
        canonical = self._embedding_store.get_embedding(db, avatar_id)
        results: list[dict[str, Any]] = []
        for i, frame_emb in enumerate(frame_embeddings):
            if canonical is not None:
                sim = _cosine_similarity(canonical, frame_emb)
            else:
                sim = 1.0  # no canonical → all frames pass
            results.append({
                "frame_index": i,
                "cosine_similarity": sim,
                "drift_detected": sim < _EMBEDDING_DRIFT_THRESHOLD,
            })
        return results


class AvatarIdentityService:
    def __init__(self) -> None:
        self._embedding_store = AvatarEmbeddingStore()
        self._guard = AvatarConsistencyGuard()

    def upsert_identity(self, db: Session, avatar_id: str, data: dict) -> AvatarDna:
        avatar = _repo.get_avatar(db, avatar_id)
        if not avatar:
            data["id"] = avatar_id
            return _repo.create_avatar(db, data)
        return _repo.update_avatar(db, avatar_id, data)

    def upsert_visual(self, db: Session, avatar_id: str, data: dict) -> AvatarVisualDna:
        visual = _repo.upsert_visual(db, avatar_id, data)
        # If source media is provided, extract and store embedding
        source_media = data.get("source_media_path") or data.get("source_media_url")
        if source_media and "embedding_vector" not in data:
            try:
                from app.services.avatar.media_embedding_extractor import MediaEmbeddingExtractor
                extractor = MediaEmbeddingExtractor()
                embedding = extractor.extract(source_media)
                visual = _repo.upsert_visual(db, avatar_id, {"embedding_vector": embedding})
            except Exception:
                pass
        return visual

    def upsert_voice(self, db: Session, avatar_id: str, data: dict) -> AvatarVoiceDna:
        return _repo.upsert_voice(db, avatar_id, data)

    def upsert_motion(self, db: Session, avatar_id: str, data: dict) -> AvatarMotionDna:
        return _repo.upsert_motion(db, avatar_id, data)

    # ------------------------------------------------------------------
    # Identity vector & reference frames
    # ------------------------------------------------------------------

    def get_identity_vector(self, db: Session, avatar_id: str) -> dict[str, Any]:
        """Return a compact identity vector for the avatar."""
        avatar = _repo.get_avatar(db, avatar_id)
        if not avatar:
            return {}
        visual = _repo.get_visual(db, avatar_id)
        voice = _repo.get_voice(db, avatar_id)
        motion = _repo.get_motion(db, avatar_id)

        vector: dict[str, Any] = {
            "avatar_id": avatar_id,
            "niche_code": avatar.niche_code,
            "market_code": avatar.market_code,
        }
        if visual:
            for field in _FACE_SIMILARITY_FIELDS + _STYLE_SIMILARITY_FIELDS:
                vector[field] = getattr(visual, field, None)
            vector["reference_image_url"] = visual.reference_image_url
            # Include embedding when available
            if visual.embedding_vector:
                vector["has_embedding"] = True
        if voice:
            vector["language_code"] = voice.language_code
            vector["tone"] = voice.tone
        if motion:
            for field in _MOTION_CONSISTENCY_FIELDS:
                vector[field] = getattr(motion, field, None)

        return vector

    def get_reference_frames(
        self,
        avatar_id: str,
        db: Session | None = None,
    ) -> list[dict[str, Any]]:
        """Return canonical reference frames for consistency scoring.

        When a DB session is provided, reads from the ``avatar_reference_frames``
        table.  Falls back to static placeholders when the table is empty or
        no DB session is available.
        """
        if db is not None:
            try:
                from app.models.autovis import AvatarReferenceFrame
                rows = (
                    db.query(AvatarReferenceFrame)
                    .filter(AvatarReferenceFrame.avatar_id == avatar_id)
                    .order_by(AvatarReferenceFrame.created_at)
                    .all()
                )
                if rows:
                    return [
                        {
                            "frame_type": r.frame_type,
                            "avatar_id": avatar_id,
                            "image_url": r.image_url,
                            "embedding_vector": r.embedding_vector,
                            "source": "db",
                        }
                        for r in rows
                    ]
            except Exception:
                pass
        # Static placeholders
        return [
            {"frame_type": "face_neutral", "avatar_id": avatar_id, "source": "static"},
            {"frame_type": "pose_default", "avatar_id": avatar_id, "source": "animated"},
            {"frame_type": "style_primary", "avatar_id": avatar_id, "source": "static"},
        ]

    # ------------------------------------------------------------------
    # Embedding-based cosine similarity check
    # ------------------------------------------------------------------

    def score_embedding_similarity(
        self,
        db: Session,
        avatar_id: str,
        candidate_embedding: list[float],
    ) -> float:
        """Return cosine similarity between avatar's canonical embedding and a render output embedding."""
        return self._embedding_store.similarity(db, avatar_id, candidate_embedding)

    # ------------------------------------------------------------------
    # Frame sequence identity lock
    # ------------------------------------------------------------------

    def lock_frame_sequence(
        self,
        db: Session,
        avatar_id: str,
        frame_embeddings: list[list[float]],
    ) -> list[dict[str, Any]]:
        """Score each frame against the avatar's canonical embedding.

        Returns per-frame drift scores.  Frames with ``drift_detected=True``
        should be flagged for manual review or re-render.
        """
        return self._guard.lock_frame_sequence(db, avatar_id, frame_embeddings)

    # ------------------------------------------------------------------
    # Render-time verification loop
    # ------------------------------------------------------------------

    # Number of frames to sample from the output video for identity verification
    # when the caller does not supply pre-computed embeddings.
    _VERIFY_N_FRAMES: int = 8

    def verify_render_output(
        self,
        db: Session,
        avatar_id: str,
        render_url: str,
        frame_count: int = 0,
        frame_embeddings: list[list[float]] | None = None,
    ) -> dict[str, Any]:
        """Verify that a completed render is consistent with the avatar's identity.

        Full gate loop: extracts per-frame embeddings, compares against the
        canonical AvatarReferenceFrame, and raises ``IdentityDriftException``
        when similarity falls below ``IDENTITY_GATE_THRESHOLD``.

        When ``frame_embeddings`` is not supplied, the method uses
        ``MediaEmbeddingExtractor`` to sample ``_VERIFY_N_FRAMES`` frames
        directly from ``render_url`` and compute per-frame cosine similarity.
        This ensures the gate is applied to the *actual output video* rather
        than falling back to a static identity field.

        Returns a result dict including ``consistency_score``, ``ok`` (bool),
        ``action`` ("accept" | "identity_review"), and ``frame_results``.
        """
        from app.services.avatar.media_embedding_extractor import MediaEmbeddingExtractor

        frame_results: list[dict[str, Any]] = []
        consistency_score: float = 1.0
        extraction_method: str = "provided"
        extraction_failed: bool = False

        if frame_embeddings:
            # Use caller-supplied embeddings (fastest path)
            frame_results = self.lock_frame_sequence(db, avatar_id, frame_embeddings)
            scores = [r["cosine_similarity"] for r in frame_results]
            consistency_score = round(sum(scores) / len(scores), 3) if scores else 1.0
        elif render_url:
            # Extract embeddings from the actual output video/image using
            # MediaEmbeddingExtractor.  extract(url, n_frames=N) samples N
            # evenly-spaced frames and returns their mean embedding as a single
            # list[float].  We pass this single vector to lock_frame_sequence
            # which compares it against the canonical reference frame.
            extraction_method = "media_extractor"
            try:
                extractor = MediaEmbeddingExtractor()
                mean_embedding: list[float] = extractor.extract(
                    render_url, n_frames=self._VERIFY_N_FRAMES
                )
                # Wrap in a list so lock_frame_sequence receives list[list[float]]
                frame_results = self.lock_frame_sequence(db, avatar_id, [mean_embedding])
                scores = [r["cosine_similarity"] for r in frame_results]
                consistency_score = round(sum(scores) / len(scores), 3) if scores else 1.0
            except Exception as _exc:
                # Extraction failed — fall back to static identity field, but cap the
                # score so the render is routed to identity_review instead of silently
                # accepted.  Callers can inspect extraction_failed=True to handle this.
                extraction_method = "identity_fallback"
                extraction_failed = True
                logger.warning(
                    "verify_render_output: embedding extraction failed for avatar=%s url=%s — "
                    "falling back to static identity score: %s",
                    avatar_id, render_url, _exc,
                )
                identity = self.get_identity_vector(db, avatar_id)
                raw_score = (
                    identity.get("consistency_score", 1.0)
                    if isinstance(identity.get("consistency_score"), float)
                    else 1.0
                )
                # Cap at just below _RENDER_CONSISTENCY_THRESHOLD so the action is
                # always "identity_review" when we could not actually inspect the render.
                consistency_score = round(
                    min(raw_score, _RENDER_CONSISTENCY_THRESHOLD - 0.001), 3
                )
        else:
            # No render URL provided: use static identity field as last resort
            extraction_method = "identity_fallback"
            identity = self.get_identity_vector(db, avatar_id)
            consistency_score = round(
                identity.get("consistency_score", 1.0)
                if isinstance(identity.get("consistency_score"), float)
                else 1.0,
                3,
            )

        # Identity gate: raise when below threshold
        if consistency_score < IDENTITY_GATE_THRESHOLD:
            # Phase 2.2: record failure for drift-triggered refresh
            try:
                from app.services.avatar.canonical_reference_scheduler import (
                    record_verification_failure,
                    record_verification_success,
                )
                if consistency_score < _TEMPORAL_CONTINUITY_THRESHOLD:
                    fail_count = record_verification_failure(avatar_id)
                    logger.debug(
                        "verify_render_output: drift failure count=%d avatar=%s",
                        fail_count, avatar_id,
                    )
                else:
                    record_verification_success(avatar_id)
            except Exception:
                pass
            raise IdentityDriftException(avatar_id, consistency_score)
        else:
            # Reset failure count on success
            try:
                from app.services.avatar.canonical_reference_scheduler import record_verification_success
                record_verification_success(avatar_id)
            except Exception:
                pass

        action = "accept" if consistency_score >= _RENDER_CONSISTENCY_THRESHOLD else "identity_review"
        effective_frame_count = frame_count or len(frame_results) or len(frame_embeddings or [])
        return {
            "ok": True,
            "avatar_id": avatar_id,
            "render_url": render_url,
            "frame_count": effective_frame_count,
            "consistency_score": consistency_score,
            "action": action,
            "requires_review": action == "identity_review",
            "frame_results": frame_results,
            "extraction_method": extraction_method,
            "extraction_failed": extraction_failed,
        }

    # ------------------------------------------------------------------
    # Consistency scoring
    # ------------------------------------------------------------------

    def score_consistency(
        self,
        db: Session,
        avatar_id: str,
        output_traits: dict[str, Any],
    ) -> dict[str, Any]:
        """Compare output_traits against the avatar's stored identity vector."""
        identity = self.get_identity_vector(db, avatar_id)
        if not identity:
            return {
                "ok": False,
                "error": "avatar_not_found",
                "consistency_score": 0.0,
                "drift_flags": ["avatar_not_found"],
            }

        # Use embedding-based similarity when available
        candidate_emb: list[float] | None = output_traits.get("embedding_vector")
        if candidate_emb is not None and identity.get("has_embedding"):
            emb_sim = self._embedding_store.similarity(db, avatar_id, candidate_emb)
            drift_flags: list[str] = []
            if emb_sim < _EMBEDDING_DRIFT_THRESHOLD:
                drift_flags.append("embedding_drift_detected")
            return {
                "ok": True,
                "avatar_id": avatar_id,
                "embedding_similarity": emb_sim,
                "consistency_score": emb_sim,
                "drift_flags": drift_flags,
                "should_reject": emb_sim < _EMBEDDING_DRIFT_THRESHOLD,
                "method": "embedding",
            }

        # Fall back to field-level matching
        face_sim = self._compute_field_similarity(identity, output_traits, _FACE_SIMILARITY_FIELDS)
        style_sim = self._compute_field_similarity(identity, output_traits, _STYLE_SIMILARITY_FIELDS)
        motion_cons = self._compute_field_similarity(identity, output_traits, _MOTION_CONSISTENCY_FIELDS)

        overall = round((face_sim * 0.4 + style_sim * 0.35 + motion_cons * 0.25), 3)

        drift_flags = []
        if face_sim < _FACE_DRIFT_THRESHOLD:
            drift_flags.append("face_drift_detected")
        if style_sim < _STYLE_DRIFT_THRESHOLD:
            drift_flags.append("style_drift_detected")
        if motion_cons < _MOTION_DRIFT_THRESHOLD:
            drift_flags.append("motion_drift_detected")

        return {
            "ok": True,
            "avatar_id": avatar_id,
            "face_similarity": round(face_sim, 3),
            "style_similarity": round(style_sim, 3),
            "motion_consistency": round(motion_cons, 3),
            "consistency_score": overall,
            "drift_flags": drift_flags,
            "should_reject": len(drift_flags) >= 2 or face_sim < _FACE_DRIFT_THRESHOLD,
            "method": "field_matching",
        }

    @staticmethod
    def _compute_field_similarity(
        reference: dict[str, Any],
        candidate: dict[str, Any],
        fields: tuple[str, ...],
    ) -> float:
        """Return fraction of fields that match between reference and candidate."""
        present = 0
        matched = 0
        for field in fields:
            ref_val = reference.get(field)
            cand_val = candidate.get(field)
            if ref_val is not None:
                present += 1
                if ref_val == cand_val:
                    matched += 1
                elif isinstance(ref_val, str) and isinstance(cand_val, str):
                    if ref_val.lower() in cand_val.lower() or cand_val.lower() in ref_val.lower():
                        matched += 0.5
        if present == 0:
            return 1.0
        return matched / present



# ---------------------------------------------------------------------------
# Temporal Identity Continuity Checker (Phase 2A)
# ---------------------------------------------------------------------------

class TemporalIdentityContinuityChecker:
    """Check temporal identity continuity across consecutive render frames.

    ``check()`` samples ``n_frames`` from a render, computes consecutive-frame
    cosine similarity, and returns a violations list where similarity drops
    below ``_TEMPORAL_CONTINUITY_THRESHOLD``.
    """

    def check(
        self,
        render_path: str,
        n_frames: int = 10,
    ) -> list[dict[str, Any]]:
        """Sample frames from ``render_path`` and check consecutive similarity.

        Returns a list of violation dicts.  Each violation contains:
        - ``frame_a``: index of the first frame
        - ``frame_b``: index of the second frame
        - ``similarity``: cosine similarity between them
        """
        from app.services.avatar.media_embedding_extractor import MediaEmbeddingExtractor

        extractor = MediaEmbeddingExtractor()
        # Generate per-frame embeddings (stub uses deterministic hashing)
        embeddings: list[list[float]] = []
        for i in range(n_frames):
            frame_source = f"{render_path}:frame:{i}"
            emb = extractor.extract(frame_source, n_frames=1)
            embeddings.append(emb)

        violations: list[dict[str, Any]] = []
        for i in range(len(embeddings) - 1):
            sim = _cosine_similarity(embeddings[i], embeddings[i + 1])
            if sim < _TEMPORAL_CONTINUITY_THRESHOLD:
                violations.append({
                    "frame_a": i,
                    "frame_b": i + 1,
                    "similarity": round(sim, 4),
                    "threshold": _TEMPORAL_CONTINUITY_THRESHOLD,
                })
        return violations


# ---------------------------------------------------------------------------
# Canonical Reference Refresher (Phase 2A)
# ---------------------------------------------------------------------------

class CanonicalReferenceRefresher:
    """Refresh the canonical AvatarReferenceFrame after a successful render.

    ``refresh_after_success()`` selects the highest-quality frame from
    ``render_frames`` (by embedding norm as a quality proxy) and upserts it
    as the new canonical reference.
    """

    def refresh_after_success(
        self,
        db: Session,
        avatar_id: str,
        render_frames: list[list[float]],
        frame_type: str = "face_neutral",
        image_url: Optional[str] = None,
    ) -> Optional[Any]:
        """Upsert AvatarReferenceFrame with the highest-quality render frame.

        Returns the upserted row, or None if no frames are provided or an error
        occurs.
        """
        if not render_frames:
            return None
        try:
            from app.models.autovis import AvatarReferenceFrame

            # Select frame with highest L2 norm as quality proxy
            def _norm(v: list[float]) -> float:
                return math.sqrt(sum(x * x for x in v))

            best_frame = max(render_frames, key=_norm)

            existing = (
                db.query(AvatarReferenceFrame)
                .filter(
                    AvatarReferenceFrame.avatar_id == avatar_id,
                    AvatarReferenceFrame.frame_type == frame_type,
                )
                .first()
            )
            if existing is not None:
                existing.embedding_vector = best_frame
                if image_url:
                    existing.image_url = image_url
                db.add(existing)
            else:
                row = AvatarReferenceFrame(
                    avatar_id=avatar_id,
                    frame_type=frame_type,
                    embedding_vector=best_frame,
                    image_url=image_url,
                )
                db.add(row)
            db.commit()
            return existing or row  # type: ignore[return-value]
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Phase 2.3: Temporal Identity Continuity Tracker
# ---------------------------------------------------------------------------


class TemporalIdentityTracker:
    """Track identity continuity across a sequence of render clips.

    ``track_sequence()`` computes pairwise cosine similarities between
    consecutive render embeddings and identifies weak links (pairs below
    _TEMPORAL_CONTINUITY_THRESHOLD).
    """

    def track_sequence(
        self,
        render_urls: list[str],
        avatar_id: str,
    ) -> dict[str, Any]:
        """Compute inter-clip identity continuity for a sequence of renders.

        Args:
            render_urls: Ordered list of render URL strings.
            avatar_id: The avatar's identifier (used for logging).

        Returns:
            Dict with:
            - ``continuity_score``: mean pairwise cosine similarity (0–1)
            - ``weak_links``: list of (url_a, url_b, similarity) pairs
              where similarity < _TEMPORAL_CONTINUITY_THRESHOLD
            - ``pair_scores``: all pairwise similarity values
        """
        from app.services.avatar.media_embedding_extractor import MediaEmbeddingExtractor

        if len(render_urls) < 2:
            return {
                "continuity_score": 1.0,
                "weak_links": [],
                "pair_scores": [],
                "avatar_id": avatar_id,
            }

        extractor = MediaEmbeddingExtractor()
        embeddings: list[list[float]] = []
        for url in render_urls:
            try:
                emb = extractor.extract(url, n_frames=4)
                embeddings.append(emb)
            except Exception as exc:
                logger.debug("TemporalIdentityTracker: extraction failed url=%s: %s", url, exc)
                embeddings.append([0.0] * 128)

        pair_scores: list[dict[str, Any]] = []
        similarities: list[float] = []
        weak_links: list[dict[str, Any]] = []

        for i in range(len(embeddings) - 1):
            sim = _cosine_similarity(embeddings[i], embeddings[i + 1])
            similarities.append(sim)
            pair = {
                "url_a": render_urls[i],
                "url_b": render_urls[i + 1],
                "similarity": sim,
            }
            pair_scores.append(pair)
            if sim < _TEMPORAL_CONTINUITY_THRESHOLD:
                weak_links.append(pair)

        continuity_score = round(
            sum(similarities) / len(similarities) if similarities else 1.0, 4
        )
        return {
            "continuity_score": continuity_score,
            "weak_links": weak_links,
            "pair_scores": pair_scores,
            "avatar_id": avatar_id,
        }
