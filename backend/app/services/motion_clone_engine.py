from __future__ import annotations

from app.schemas.motion_clone import MotionCloneRequest, MotionCloneResponse


class MotionCloneEngine:
    def plan(self, req: MotionCloneRequest) -> MotionCloneResponse:
        source = req.reference_video_url or req.reference_motion_text or "reference"
        beat_profile = req.beat_profile or {"bpm": 96, "intensity": "medium"}

        beat_sync_map = [
            {"beat_index": 1, "action": "intro_pose", "time_sec": 0.0},
            {"beat_index": 2, "action": "gesture_emphasis", "time_sec": 1.2},
            {"beat_index": 3, "action": "camera_shift", "time_sec": 2.4},
        ]

        motion_plan = {
            "source": source,
            "style": "clone_with_adaptation",
            "avatar_id": req.avatar_id,
            "market_code": req.market_code,
            "beat_profile": beat_profile,
        }

        guidance = {
            "lip_sync_mode": "adaptive",
            "gesture_density": "moderate",
            "transitions": "beat-aligned",
            "safety_clamps": {"max_rotation_deg": 35},
        }

        return MotionCloneResponse(
            motion_plan=motion_plan,
            beat_sync_map=beat_sync_map,
            animation_guidance_payload=guidance,
        )
