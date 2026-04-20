from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.schemas.scoring import CandidateScore
from app.schemas.lookbook import LookbookRequest, LookbookResponse

# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------
_SCORE_WEIGHTS: dict[str, float] = {
    "style_coherence": 0.27,
    "product_compatibility": 0.28,
    "campaign_fit": 0.25,
    "localization_fit": 0.20,
}

_PLATFORM_COHERENCE_MAP: dict[str, float] = {
    "shorts": 0.88,
    "reels": 0.87,
    "tiktok": 0.84,
    "instagram": 0.86,
    "youtube": 0.80,
}

_STYLE_CAMPAIGN_MAP: dict[str, dict[str, float]] = {
    "clean-commerce": {"conversion": 0.92, "awareness": 0.78, "engagement": 0.80},
    "editorial": {"awareness": 0.90, "engagement": 0.86, "conversion": 0.72},
    "ugc-dynamic": {"engagement": 0.93, "conversion": 0.85, "awareness": 0.76},
}


def _product_compatibility_score(products: list[dict[str, Any]]) -> float:
    """Score compatibility based on style/category diversity within the batch."""
    if not products:
        return 0.60
    styles = {str(p.get("style", "")).lower() for p in products if p.get("style")}
    categories = {str(p.get("category", "")).lower() for p in products if p.get("category")}
    # More consistent styles → higher compatibility
    style_score = 0.90 if len(styles) <= 1 else max(0.60, 0.90 - (len(styles) - 1) * 0.06)
    category_score = 0.88 if len(categories) <= 2 else max(0.62, 0.88 - (len(categories) - 2) * 0.04)
    return round((style_score * 0.6 + category_score * 0.4), 3)


def _campaign_fit_score(style_preset: str, target_platform: str | None) -> float:
    """Score based on style + campaign goal derived from platform context."""
    platform_key = (target_platform or "shorts").lower()
    # Infer campaign goal from platform (simplified rule)
    if platform_key in {"tiktok", "reels", "shorts"}:
        goal_key = "engagement"
    elif platform_key in {"instagram"}:
        goal_key = "awareness"
    else:
        goal_key = "conversion"
    style_map = _STYLE_CAMPAIGN_MAP.get(style_preset, {})
    return round(style_map.get(goal_key, 0.72), 3)


def _localization_fit_score(market_code: str | None) -> float:
    """Higher when market locale is explicitly specified."""
    if not market_code:
        return 0.65
    return round(min(0.92, 0.70 + len(market_code) * 0.025), 3)


def _style_coherence_score(style_preset: str, target_platform: str | None) -> float:
    """Coherence of the style with the target platform."""
    platform_key = (target_platform or "shorts").lower()
    base = _PLATFORM_COHERENCE_MAP.get(platform_key, 0.76)
    # Some styles are more coherent on specific platforms
    if style_preset == "ugc-dynamic" and platform_key in {"tiktok", "reels", "shorts"}:
        base = min(0.97, base + 0.06)
    elif style_preset == "editorial" and platform_key in {"instagram", "youtube"}:
        base = min(0.97, base + 0.05)
    return round(base, 3)


class LookbookEngine:
    def generate(self, req: LookbookRequest, db=None) -> LookbookResponse:
        """Generate lookbook. If ``db`` (SQLAlchemy Session) is provided the
        run is persisted in ``creative_engine_runs``."""
        run_record = None
        if db is not None:
            from app.models.creative_engine_run import CreativeEngineRun
            run_record = CreativeEngineRun(
                engine_type="lookbook",
                status="running",
                input_payload=req.model_dump(),
                started_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            db.add(run_record)
            db.commit()
            db.refresh(run_record)

        try:
            result = self._generate_internal(req)
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

    def _generate_internal(self, req: LookbookRequest) -> LookbookResponse:
        candidate_styles = [req.style_preset or "clean-commerce", "editorial", "ugc-dynamic"]
        candidate_payloads: list[tuple[list[dict[str, Any]], list[dict[str, Any]], CandidateScore]] = []

        for style in candidate_styles:
            outfits = self._build_outfits(req.products)
            scene_pack = self._build_scene_pack(outfits, style)

            coherence = _style_coherence_score(style, req.target_platform)
            compatibility = _product_compatibility_score(req.products)
            campaign_fit = _campaign_fit_score(style, req.target_platform)
            localization_fit = _localization_fit_score(req.market_code)

            total = round(
                (coherence * _SCORE_WEIGHTS["style_coherence"])
                + (compatibility * _SCORE_WEIGHTS["product_compatibility"])
                + (campaign_fit * _SCORE_WEIGHTS["campaign_fit"])
                + (localization_fit * _SCORE_WEIGHTS["localization_fit"]),
                3,
            )
            candidate_payloads.append(
                (
                    outfits,
                    scene_pack,
                    CandidateScore(
                        candidate_id=f"lookbook_{style}",
                        score_total=total,
                        score_breakdown={
                            "style_coherence": coherence,
                            "product_compatibility": compatibility,
                            "campaign_fit": campaign_fit,
                            "localization_fit": localization_fit,
                        },
                        rationale=(
                            f"Style '{style}' scored by platform coherence "
                            f"({req.target_platform or 'shorts'}), "
                            f"product compatibility ({len(req.products)} items), "
                            f"campaign goal fit, and locale ({req.market_code or 'unset'})."
                        ),
                        metadata={"style": style},
                    ),
                )
            )

        winner_payload = max(candidate_payloads, key=lambda item: item[2].score_total)
        outfits, scene_pack, winner_score = winner_payload
        candidates = [item[2] for item in candidate_payloads]
        for score in candidates:
            score.winner_flag = score.candidate_id == winner_score.candidate_id

        video_plan = {
            "target_platform": req.target_platform or "shorts",
            "scene_count": len(scene_pack),
            "narrative": "showcase -> styling_tip -> call_to_action",
            "collection_name": req.collection_name,
        }
        return LookbookResponse(
            lookbook_id=str(uuid.uuid4()),
            outfit_sequences=outfits,
            scene_pack=scene_pack,
            video_plan=video_plan,
            candidates=candidates,
            winner_candidate_id=winner_score.candidate_id,
        )

    @staticmethod
    def _build_outfits(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
        outfits: list[dict[str, Any]] = []
        batch_size = 3
        for idx in range(0, len(products), batch_size):
            chunk = products[idx : idx + batch_size]
            if not chunk:
                continue
            outfits.append(
                {
                    "sequence_index": len(outfits) + 1,
                    "products": chunk,
                    "theme": chunk[0].get("style") or "signature",
                }
            )
        return outfits

    @staticmethod
    def _build_scene_pack(outfits: list[dict[str, Any]], style_preset: str | None) -> list[dict[str, Any]]:
        scenes: list[dict[str, Any]] = []
        for outfit in outfits:
            scenes.append(
                {
                    "scene_index": len(scenes) + 1,
                    "title": f"Outfit Set {outfit['sequence_index']}",
                    "shot_hint": "full-body editorial pan",
                    "style": style_preset or "clean-commerce",
                    "metadata": {"sequence_index": outfit["sequence_index"]},
                }
            )
        return scenes

    @staticmethod
    def score_weights() -> dict[str, Any]:
        """Expose scoring weights for audit / QA inspection."""
        return dict(_SCORE_WEIGHTS)
