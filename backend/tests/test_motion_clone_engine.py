from __future__ import annotations

from app.schemas.motion_clone import MotionCloneRequest
from app.services.motion_clone_engine import MotionCloneEngine


def test_reference_input_to_motion_plan() -> None:
    engine = MotionCloneEngine()
    result = engine.plan(MotionCloneRequest(reference_motion_text="fast punchy rhythm"))
    assert result.motion_plan


def test_has_beat_sync_map() -> None:
    engine = MotionCloneEngine()
    result = engine.plan(MotionCloneRequest(reference_motion_text="fast punchy rhythm"))
    assert result.beat_sync_map


def test_animation_guidance_payload_not_empty() -> None:
    engine = MotionCloneEngine()
    result = engine.plan(MotionCloneRequest(reference_motion_text="fast punchy rhythm"))
    assert result.animation_guidance_payload
