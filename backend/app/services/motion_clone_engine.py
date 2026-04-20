from __future__ import annotations

from app.schemas.scoring import CandidateScore
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
        candidates = [
            CandidateScore(
                candidate_id="motion_strict_clone",
                score_total=0.81,
                score_breakdown={
                    "motion_consistency": 0.89,
                    "brand_persona_fit": 0.74,
                    "clip_usability": 0.8,
                    "reuse_score": 0.78,
                },
                rationale="Best raw movement continuity with moderate persona adaptation.",
            ),
            CandidateScore(
                candidate_id="motion_balanced_adaptation",
                score_total=0.84,
                score_breakdown={
                    "motion_consistency": 0.84,
                    "brand_persona_fit": 0.83,
                    "clip_usability": 0.82,
                    "reuse_score": 0.86,
                },
                rationale="Balances consistency and persona fit with stronger reuse value.",
            ),
            CandidateScore(
                candidate_id="motion_creative_remix",
                score_total=0.73,
                score_breakdown={
                    "motion_consistency": 0.69,
                    "brand_persona_fit": 0.76,
                    "clip_usability": 0.71,
                    "reuse_score": 0.75,
                },
                rationale="Higher creative variance but lower deterministic consistency.",
            ),
        ]
        winner = max(candidates, key=lambda c: c.score_total)
        winner.winner_flag = True

        return MotionCloneResponse(
            motion_plan=motion_plan,
            beat_sync_map=beat_sync_map,
            animation_guidance_payload=guidance,
            candidates=candidates,
            winner_candidate_id=winner.candidate_id,
        )
