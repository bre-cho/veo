from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.scoring import CandidateScore
from app.schemas.motion_clone import MotionCloneRequest, MotionCloneResponse

# ---------------------------------------------------------------------------
# Scoring weights for motion clone candidates
# ---------------------------------------------------------------------------
_SCORE_WEIGHTS: dict[str, float] = {
    "motion_consistency": 0.30,
    "brand_persona_fit": 0.28,
    "clip_usability": 0.22,
    "reuse_score": 0.20,
}

_INTENSITY_CONSISTENCY_MAP: dict[str, dict[str, float]] = {
    "high":   {"strict_clone": 0.92, "balanced": 0.82, "creative_remix": 0.65},
    "medium": {"strict_clone": 0.84, "balanced": 0.87, "creative_remix": 0.73},
    "low":    {"strict_clone": 0.78, "balanced": 0.82, "creative_remix": 0.80},
}

_PLATFORM_PERSONA_MAP: dict[str, float] = {
    "tiktok": 0.88,
    "reels":  0.86,
    "shorts": 0.84,
    "youtube": 0.78,
    "instagram": 0.80,
}

_CLIP_GOAL_USABILITY: dict[str, dict[str, float]] = {
    "hook":       {"strict_clone": 0.82, "balanced": 0.85, "creative_remix": 0.79},
    "demo":       {"strict_clone": 0.88, "balanced": 0.84, "creative_remix": 0.72},
    "testimonial":{"strict_clone": 0.78, "balanced": 0.86, "creative_remix": 0.83},
    "cta":        {"strict_clone": 0.80, "balanced": 0.83, "creative_remix": 0.76},
    "default":    {"strict_clone": 0.80, "balanced": 0.82, "creative_remix": 0.74},
}


def _motion_consistency(intensity: str, style_key: str) -> float:
    row = _INTENSITY_CONSISTENCY_MAP.get(intensity.lower(), _INTENSITY_CONSISTENCY_MAP["medium"])
    return round(row.get(style_key, 0.78), 3)


def _brand_persona_fit(market_code: str | None, avatar_id: str | None, style_key: str) -> float:
    """More context → more confident persona fit score."""
    base = _PLATFORM_PERSONA_MAP.get("shorts", 0.78)
    if avatar_id:
        base = min(0.96, base + 0.06)
    if market_code:
        base = min(0.96, base + 0.04)
    # Creative remix is better at persona adaptation
    if style_key == "creative_remix":
        base = min(0.96, base + 0.04)
    elif style_key == "strict_clone":
        base = max(0.55, base - 0.06)
    return round(base, 3)


def _clip_usability(clip_goal: str | None, style_key: str) -> float:
    goal_key = (clip_goal or "default").lower()
    row = _CLIP_GOAL_USABILITY.get(goal_key, _CLIP_GOAL_USABILITY["default"])
    return round(row.get(style_key, 0.76), 3)


def _reuse_score(beat_bpm: int, intensity: str, style_key: str) -> float:
    """Higher BPM + medium intensity → better reuse; strict clone scores lower on reuse."""
    bpm_factor = min(0.10, (beat_bpm - 80) / 500.0) if beat_bpm > 80 else 0.0
    base_map = {"strict_clone": 0.72, "balanced": 0.86, "creative_remix": 0.76}
    base = base_map.get(style_key, 0.76)
    if intensity == "high":
        base = min(0.96, base + 0.04)
    return round(min(0.96, base + bpm_factor), 3)


def _candidate_total(mc: float, bp: float, cu: float, rs: float) -> float:
    return round(
        (mc * _SCORE_WEIGHTS["motion_consistency"])
        + (bp * _SCORE_WEIGHTS["brand_persona_fit"])
        + (cu * _SCORE_WEIGHTS["clip_usability"])
        + (rs * _SCORE_WEIGHTS["reuse_score"]),
        3,
    )


class MotionCloneEngine:
    def plan(self, req: MotionCloneRequest, db=None) -> MotionCloneResponse:
        """Plan motion clone. If ``db`` (SQLAlchemy Session) is provided the
        run is persisted in ``creative_engine_runs``."""
        run_record = None
        if db is not None:
            from app.models.creative_engine_run import CreativeEngineRun
            run_record = CreativeEngineRun(
                engine_type="motion_clone",
                status="running",
                input_payload=req.model_dump(),
                started_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            db.add(run_record)
            db.commit()
            db.refresh(run_record)

        try:
            result = self._plan_internal(req)
            if run_record is not None:
                run_record.status = "completed"
                run_record.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                run_record.candidates = [c.model_dump() for c in result.candidates]
                run_record.winner_candidate_id = result.winner_candidate_id
                run_record.output_payload = result.model_dump()
                db.add(run_record)
                db.commit()
                result.run_id = run_record.id  # type: ignore[attr-defined]
            return result
        except Exception as exc:
            if run_record is not None:
                run_record.status = "failed"
                run_record.error_message = str(exc)
                run_record.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                db.add(run_record)
                db.commit()
            raise

    def _plan_internal(self, req: MotionCloneRequest) -> MotionCloneResponse:
        source = req.reference_video_url or req.reference_motion_text or "reference"
        beat_profile = req.beat_profile or {"bpm": 96, "intensity": "medium"}
        bpm: int = int(beat_profile.get("bpm", 96))
        intensity: str = str(beat_profile.get("intensity", "medium"))

        beat_sync_map = [
            {"beat_index": 1, "action": "intro_pose", "time_sec": 0.0},
            {"beat_index": 2, "action": "gesture_emphasis", "time_sec": round(60.0 / max(bpm, 1), 2)},
            {"beat_index": 3, "action": "camera_shift", "time_sec": round(120.0 / max(bpm, 1), 2)},
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
            "gesture_density": "moderate" if intensity == "medium" else ("dense" if intensity == "high" else "sparse"),
            "transitions": "beat-aligned",
            "safety_clamps": {"max_rotation_deg": 35},
        }

        # Build 3 deterministic candidates scored from input, not position
        styles = [
            ("motion_strict_clone",        "strict_clone"),
            ("motion_balanced_adaptation", "balanced"),
            ("motion_creative_remix",      "creative_remix"),
        ]

        clip_goal: str | None = req.beat_profile.get("clip_goal") if req.beat_profile else None

        candidates: list[CandidateScore] = []
        for cid, style_key in styles:
            mc = _motion_consistency(intensity, style_key)
            bp = _brand_persona_fit(req.market_code, req.avatar_id, style_key)
            cu = _clip_usability(clip_goal, style_key)
            rs = _reuse_score(bpm, intensity, style_key)
            total = _candidate_total(mc, bp, cu, rs)
            candidates.append(
                CandidateScore(
                    candidate_id=cid,
                    score_total=total,
                    score_breakdown={
                        "motion_consistency": mc,
                        "brand_persona_fit": bp,
                        "clip_usability": cu,
                        "reuse_score": rs,
                    },
                    rationale=(
                        f"Scored from intensity='{intensity}', bpm={bpm}, "
                        f"avatar={req.avatar_id or 'unset'}, market={req.market_code or 'unset'}, "
                        f"clip_goal={clip_goal or 'default'}."
                    ),
                )
            )

        winner = max(candidates, key=lambda c: c.score_total)
        winner.winner_flag = True

        return MotionCloneResponse(
            motion_plan=motion_plan,
            beat_sync_map=beat_sync_map,
            animation_guidance_payload=guidance,
            candidates=candidates,
            winner_candidate_id=winner.candidate_id,
        )

    @staticmethod
    def score_weights() -> dict[str, float]:
        """Expose scoring weights for audit / QA inspection."""
        return dict(_SCORE_WEIGHTS)
