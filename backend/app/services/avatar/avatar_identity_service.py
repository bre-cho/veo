from __future__ import annotations

import math
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.autovis import AvatarDna, AvatarMotionDna, AvatarVisualDna, AvatarVoiceDna
from app.repositories.avatar_repo import AvatarRepo

_repo = AvatarRepo()

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


class AvatarIdentityService:
    def upsert_identity(self, db: Session, avatar_id: str, data: dict) -> AvatarDna:
        avatar = _repo.get_avatar(db, avatar_id)
        if not avatar:
            data["id"] = avatar_id
            return _repo.create_avatar(db, data)
        return _repo.update_avatar(db, avatar_id, data)

    def upsert_visual(self, db: Session, avatar_id: str, data: dict) -> AvatarVisualDna:
        return _repo.upsert_visual(db, avatar_id, data)

    def upsert_voice(self, db: Session, avatar_id: str, data: dict) -> AvatarVoiceDna:
        return _repo.upsert_voice(db, avatar_id, data)

    def upsert_motion(self, db: Session, avatar_id: str, data: dict) -> AvatarMotionDna:
        return _repo.upsert_motion(db, avatar_id, data)

    # ------------------------------------------------------------------
    # Identity vector & reference frames
    # ------------------------------------------------------------------

    def get_identity_vector(self, db: Session, avatar_id: str) -> dict[str, Any]:
        """Return a compact identity vector for the avatar.

        The vector encodes key visual, voice, and motion traits in a
        normalised dictionary suitable for downstream similarity checks.
        """
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
        if voice:
            vector["language_code"] = voice.language_code
            vector["tone"] = voice.tone
        if motion:
            for field in _MOTION_CONSISTENCY_FIELDS:
                vector[field] = getattr(motion, field, None)

        return vector

    def get_reference_frames(self, avatar_id: str) -> list[dict[str, Any]]:
        """Return canonical reference frames used for consistency scoring.

        In production these would be actual frame descriptors (embeddings).
        Here we return named reference points that consistency checks can use.
        """
        return [
            {"frame_type": "face_neutral", "avatar_id": avatar_id, "source": "static"},
            {"frame_type": "pose_default", "avatar_id": avatar_id, "source": "animated"},
            {"frame_type": "style_primary", "avatar_id": avatar_id, "source": "static"},
        ]

    # ------------------------------------------------------------------
    # Consistency scoring
    # ------------------------------------------------------------------

    def score_consistency(
        self,
        db: Session,
        avatar_id: str,
        output_traits: dict[str, Any],
    ) -> dict[str, Any]:
        """Compare output_traits against the avatar's stored identity vector.

        Returns face_similarity, style_similarity, motion_consistency scores in
        [0, 1], plus an overall ``consistency_score`` and ``drift_flags``.
        """
        identity = self.get_identity_vector(db, avatar_id)
        if not identity:
            return {
                "ok": False,
                "error": "avatar_not_found",
                "consistency_score": 0.0,
                "drift_flags": ["avatar_not_found"],
            }

        face_sim = self._compute_field_similarity(identity, output_traits, _FACE_SIMILARITY_FIELDS)
        style_sim = self._compute_field_similarity(identity, output_traits, _STYLE_SIMILARITY_FIELDS)
        motion_cons = self._compute_field_similarity(identity, output_traits, _MOTION_CONSISTENCY_FIELDS)

        overall = round((face_sim * 0.4 + style_sim * 0.35 + motion_cons * 0.25), 3)

        drift_flags: list[str] = []
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
                    # Partial string match contributes 0.5 weight
                    if ref_val.lower() in cand_val.lower() or cand_val.lower() in ref_val.lower():
                        matched += 0.5
        if present == 0:
            return 1.0  # no reference data → treat as consistent
        return matched / present
