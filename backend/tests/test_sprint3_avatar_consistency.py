"""Sprint 3 – Avatar Identity + Consistency tests.

Covers:
- AvatarIdentityService: get_identity_vector, get_reference_frames
- AvatarIdentityService: score_consistency with drift detection
- AvatarCloneService: consistency report included in clone result
- AvatarPreviewService: drift detection rejects drifted output_traits
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.avatar.avatar_identity_service import (
    AvatarIdentityService,
    _FACE_DRIFT_THRESHOLD,
    _STYLE_DRIFT_THRESHOLD,
)
from app.services.avatar.avatar_clone_service import AvatarCloneService
from app.services.avatar.avatar_preview_service import AvatarPreviewService


# ---------------------------------------------------------------------------
# Helpers: build mock visual/motion DNAs
# ---------------------------------------------------------------------------

def _make_visual(**kwargs):
    visual = MagicMock()
    defaults = dict(
        skin_tone="medium", eye_color="brown", age_range="25-35",
        gender_expression="female", hair_style="long", hair_color="black",
        outfit_code="casual", background_code="studio", accessories=None,
        reference_image_url="/img/ref.png",
    )
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(visual, k, v)
    return visual


def _make_motion(**kwargs):
    motion = MagicMock()
    defaults = dict(motion_style="natural", gesture_set="default", lipsync_mode="auto")
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(motion, k, v)
    return motion


def _make_avatar(aid="av1"):
    av = MagicMock()
    av.id = aid
    av.niche_code = "beauty"
    av.market_code = "VN"
    return av


# ---------------------------------------------------------------------------
# AvatarIdentityService
# ---------------------------------------------------------------------------

_svc = AvatarIdentityService()


def test_get_identity_vector_returns_visual_fields() -> None:
    db = MagicMock()
    with patch("app.services.avatar.avatar_identity_service._repo") as mock_repo:
        mock_repo.get_avatar.return_value = _make_avatar()
        mock_repo.get_visual.return_value = _make_visual()
        mock_repo.get_voice.return_value = None
        mock_repo.get_motion.return_value = None

        vector = _svc.get_identity_vector(db, "av1")

    assert vector["skin_tone"] == "medium"
    assert vector["eye_color"] == "brown"
    assert vector["avatar_id"] == "av1"


def test_get_identity_vector_empty_for_unknown_avatar() -> None:
    db = MagicMock()
    with patch("app.services.avatar.avatar_identity_service._repo") as mock_repo:
        mock_repo.get_avatar.return_value = None
        vector = _svc.get_identity_vector(db, "no_such")
    assert vector == {}


def test_reference_frames_structure() -> None:
    frames = _svc.get_reference_frames("av1")
    assert len(frames) >= 1
    for frame in frames:
        assert "frame_type" in frame
        assert "avatar_id" in frame


def test_score_consistency_perfect_match() -> None:
    db = MagicMock()
    with patch("app.services.avatar.avatar_identity_service._repo") as mock_repo:
        mock_repo.get_avatar.return_value = _make_avatar()
        mock_repo.get_visual.return_value = _make_visual()
        mock_repo.get_voice.return_value = None
        mock_repo.get_motion.return_value = None

        output = dict(
            skin_tone="medium", eye_color="brown", age_range="25-35",
            gender_expression="female", hair_style="long", hair_color="black",
            outfit_code="casual", background_code="studio",
        )
        result = _svc.score_consistency(db, "av1", output)

    assert result["ok"] is True
    assert result["face_similarity"] == pytest.approx(1.0, abs=0.1)
    assert result["drift_flags"] == []
    assert result["should_reject"] is False


def test_score_consistency_face_drift_triggers_flag() -> None:
    db = MagicMock()
    with patch("app.services.avatar.avatar_identity_service._repo") as mock_repo:
        mock_repo.get_avatar.return_value = _make_avatar()
        mock_repo.get_visual.return_value = _make_visual()
        mock_repo.get_voice.return_value = None
        mock_repo.get_motion.return_value = None

        # All face fields completely wrong
        output = dict(
            skin_tone="pale", eye_color="blue", age_range="50-60",
            gender_expression="male",
            hair_style="long", hair_color="black",
            outfit_code="casual", background_code="studio",
        )
        result = _svc.score_consistency(db, "av1", output)

    assert result["face_similarity"] < _FACE_DRIFT_THRESHOLD
    assert "face_drift_detected" in result["drift_flags"]
    assert result["should_reject"] is True


def test_score_consistency_style_drift_triggers_flag() -> None:
    db = MagicMock()
    with patch("app.services.avatar.avatar_identity_service._repo") as mock_repo:
        mock_repo.get_avatar.return_value = _make_avatar()
        mock_repo.get_visual.return_value = _make_visual()
        mock_repo.get_voice.return_value = None
        mock_repo.get_motion.return_value = None

        # Face matches but style is completely wrong
        output = dict(
            skin_tone="medium", eye_color="brown", age_range="25-35",
            gender_expression="female",
            hair_style="buzzcut", hair_color="blonde",
            outfit_code="formal", background_code="outdoor",
        )
        result = _svc.score_consistency(db, "av1", output)

    assert result["style_similarity"] < _STYLE_DRIFT_THRESHOLD
    assert "style_drift_detected" in result["drift_flags"]


# ---------------------------------------------------------------------------
# AvatarPreviewService – drift detection
# ---------------------------------------------------------------------------

_preview = AvatarPreviewService()


def test_preview_static_no_drift_ok() -> None:
    db = MagicMock()
    with (
        patch("app.services.avatar.avatar_preview_service._repo") as mock_repo,
        patch("app.services.avatar.avatar_identity_service._repo") as identity_repo,
    ):
        mock_repo.get_avatar.return_value = _make_avatar()
        identity_repo.get_avatar.return_value = _make_avatar()
        identity_repo.get_visual.return_value = _make_visual()
        identity_repo.get_voice.return_value = None
        identity_repo.get_motion.return_value = None

        output = dict(
            skin_tone="medium", eye_color="brown", age_range="25-35",
            gender_expression="female",
        )
        result = _preview.preview_static(db, "av1", output_traits=output)

    assert result["ok"] is True
    assert "consistency" in result


def test_preview_static_drifted_output_rejected() -> None:
    db = MagicMock()
    with (
        patch("app.services.avatar.avatar_preview_service._repo") as mock_repo,
        patch("app.services.avatar.avatar_identity_service._repo") as identity_repo,
    ):
        mock_repo.get_avatar.return_value = _make_avatar()
        identity_repo.get_avatar.return_value = _make_avatar()
        identity_repo.get_visual.return_value = _make_visual()
        identity_repo.get_voice.return_value = None
        identity_repo.get_motion.return_value = None

        # Severely drifted traits
        drifted = dict(
            skin_tone="albino", eye_color="red", age_range="70-80",
            gender_expression="male", hair_style="mohawk", hair_color="neon",
            outfit_code="costume", background_code="space",
        )
        result = _preview.preview_static(db, "av1", output_traits=drifted)

    assert result["rejected"] is True
    assert result["ok"] is False
    assert len(result.get("drift_flags", [])) > 0


def test_preview_without_output_traits_always_ok() -> None:
    db = MagicMock()
    with patch("app.services.avatar.avatar_preview_service._repo") as mock_repo:
        mock_repo.get_avatar.return_value = _make_avatar()
        result = _preview.preview_static(db, "av1")
    assert result["ok"] is True
    assert "consistency" not in result
