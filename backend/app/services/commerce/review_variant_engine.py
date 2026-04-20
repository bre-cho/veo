from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from app.services.commerce.conversion_scoring_engine import ConversionScoringEngine
from app.services.storyboard_engine import StoryboardEngine

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# In-memory history store for fallback when no DB session is provided.
_VARIANT_HISTORY: list[dict[str, Any]] = []
_MAX_HISTORY = 200

# Minimum average actual conversion score for a variant type to get a boost
_HISTORY_BOOST_THRESHOLD = 0.70
# Score boost applied to historically strong variant types
_HISTORY_SCORE_BOOST = 0.05


class ReviewVariantEngine:
    VARIANT_TYPES = ("review", "testimonial", "comparison")

    def __init__(self) -> None:
        self._scorer = ConversionScoringEngine()
        self._storyboard = StoryboardEngine()

    def generate_variants(
        self,
        product_profile: dict[str, Any],
        count: int = 5,
        *,
        platform: str | None = None,
        context: dict[str, Any] | None = None,
        db: "Session | None" = None,
    ) -> list[dict[str, Any]]:
        name = product_profile.get("product_name") or "Product"
        audience = product_profile.get("target_audience") or "customers"
        benefits = product_profile.get("benefits") or []
        pain_points = product_profile.get("pain_points") or []
        social_proof = product_profile.get("social_proof") or []
        personas = product_profile.get("personas") or []
        product_category = product_profile.get("product_category")
        market_code = product_profile.get("market_code")

        variants: list[dict[str, Any]] = []
        for idx in range(max(3, min(count, 5))):
            variant_type = self.VARIANT_TYPES[idx % len(self.VARIANT_TYPES)]

            # Use persona-specific hook when available
            persona = personas[idx % len(personas)] if personas else audience.title()
            hook = f"{persona}, are you still dealing with {pain_points[0] if pain_points else 'old workflows'}?"
            body = (
                f"{name} helps with {benefits[0] if benefits else 'faster outcomes'} "
                f"using a {variant_type} narrative."
            )
            cta = "Tap now to try it today."
            if variant_type == "comparison":
                body += " Compared to alternatives, setup is simpler and results are faster."
            if variant_type == "testimonial" and social_proof:
                body += f" {social_proof[0]}"

            storyboard = self._storyboard.generate_from_script(
                script_text="\n\n".join([hook, body, cta]),
                conversion_mode="direct",
                content_goal="conversion",
            )

            payload = {
                "variant_index": idx + 1,
                "variant_type": variant_type,
                "hook": hook,
                "body": body,
                "cta": cta,
                "storyboard_scenes": [scene.model_dump() for scene in storyboard.scenes],
                "scene_metadata": [
                    {
                        "scene_goal": scene.scene_goal,
                        "shot_hint": scene.shot_hint,
                        "pacing_weight": scene.pacing_weight,
                    }
                    for scene in storyboard.scenes
                ],
            }
            scored = self._scorer.score_variant(
                payload,
                market_code=market_code,
                persona=persona,
                product_category=product_category,
                platform=platform,
            )
            base_score = scored["score"]

            # Apply historical boost when DB data is available
            hist_boost = self._scorer.historical_boost(
                variant_type=variant_type,
                product_category=product_category,
                platform=platform,
                db=db,
            )
            payload["score"] = round(min(base_score + hist_boost, 1.0), 3)
            payload["score_breakdown"] = {
                **scored["details"],
                "historical_boost": round(hist_boost, 4),
            }
            variants.append(payload)

        return variants

    def select_winner(
        self,
        variants: list[dict[str, Any]],
        *,
        db: "Session | None" = None,
        product_name: str | None = None,
    ) -> dict[str, Any]:
        if not variants:
            return {}
        # Get historically strong variant types from DB (last 30 days)
        strong_types: set[str] = _get_historically_strong_types(
            db=db,
            product_name=product_name,
        )
        def _score(v: dict[str, Any]) -> float:
            s = float(v.get("score") or 0)
            if strong_types and v.get("variant_type") in strong_types:
                s += _HISTORY_SCORE_BOOST
            return s

        return sorted(variants, key=_score, reverse=True)[0]

    def generate_variants_with_history(
        self,
        product_profile: dict[str, Any],
        count: int = 5,
        *,
        platform: str | None = None,
        context: dict[str, Any] | None = None,
        db: "Session | None" = None,
    ) -> dict[str, Any]:
        """Generate variants, select winner, and persist run to history."""
        run_id = str(uuid.uuid4())
        variants = self.generate_variants(
            product_profile,
            count=count,
            platform=platform,
            context=context,
            db=db,
        )
        winner = self.select_winner(
            variants,
            db=db,
            product_name=product_profile.get("product_name"),
        )

        record: dict[str, Any] = {
            "run_id": run_id,
            "product_name": product_profile.get("product_name"),
            "product_category": product_profile.get("product_category"),
            "platform": platform,
            "market_code": product_profile.get("market_code"),
            "context": context or {},
            "variants": variants,
            "winner_variant_index": winner.get("variant_index"),
            "winner_score": winner.get("score"),
            "winner_score_breakdown": winner.get("score_breakdown"),
            "recorded_at": time.time(),
        }

        # Dual-write to DB when session is provided
        if db is not None:
            _db_write_run(db, record)
        else:
            # Fall back to in-memory store
            _VARIANT_HISTORY.append(record)
            if len(_VARIANT_HISTORY) > _MAX_HISTORY:
                del _VARIANT_HISTORY[: len(_VARIANT_HISTORY) - _MAX_HISTORY]

        return {
            "run_id": run_id,
            "variants": variants,
            "winner": winner,
        }

    @staticmethod
    def get_history(
        product_name: str | None = None,
        platform: str | None = None,
        limit: int = 20,
        db: "Session | None" = None,
    ) -> list[dict[str, Any]]:
        """Return recent variant history, preferring DB when available."""
        if db is not None:
            return _db_read_history(
                db,
                product_name=product_name,
                platform=platform,
                limit=limit,
            )
        # Fall back to in-memory
        records = list(reversed(_VARIANT_HISTORY))
        if product_name:
            records = [r for r in records if r.get("product_name") == product_name]
        if platform:
            records = [r for r in records if r.get("platform") == platform]
        return records[:limit]


# ---------------------------------------------------------------------------
# DB helpers (deferred imports to avoid circular deps at module load time)
# ---------------------------------------------------------------------------

def _db_write_run(db: "Session", record: dict[str, Any]) -> None:
    from app.models.variant_run_record import VariantRunRecord
    row = VariantRunRecord(
        run_id=record["run_id"],
        product_name=record.get("product_name"),
        product_category=record.get("product_category"),
        platform=record.get("platform"),
        market_code=record.get("market_code"),
        winner_variant_index=record.get("winner_variant_index"),
        winner_score=record.get("winner_score"),
        winner_score_breakdown=record.get("winner_score_breakdown"),
        variants=record.get("variants") or [],
        context=record.get("context"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)


def _db_read_history(
    db: "Session",
    *,
    product_name: str | None,
    platform: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    from app.models.variant_run_record import VariantRunRecord
    query = db.query(VariantRunRecord).order_by(VariantRunRecord.recorded_at.desc())
    if product_name:
        query = query.filter(VariantRunRecord.product_name == product_name)
    if platform:
        query = query.filter(VariantRunRecord.platform == platform)
    rows = query.limit(limit).all()
    return [
        {
            "run_id": r.run_id,
            "product_name": r.product_name,
            "product_category": r.product_category,
            "platform": r.platform,
            "market_code": r.market_code,
            "winner_variant_index": r.winner_variant_index,
            "winner_score": r.winner_score,
            "variants": r.variants,
            "context": r.context,
            "actual_conversion_score": r.actual_conversion_score,
            "recorded_at": r.recorded_at.timestamp() if r.recorded_at else None,
        }
        for r in rows
    ]


def _get_historically_strong_types(
    *,
    db: "Session | None",
    product_name: str | None,
) -> set[str]:
    """Return variant types with avg(actual_conversion_score) > threshold in last 30 days."""
    if db is None:
        return set()
    try:
        from datetime import datetime, timedelta, timezone
        from app.models.variant_run_record import VariantRunRecord

        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
        query = (
            db.query(VariantRunRecord)
            .filter(
                VariantRunRecord.actual_conversion_score.isnot(None),
                VariantRunRecord.recorded_at >= cutoff,
            )
        )
        if product_name:
            query = query.filter(VariantRunRecord.product_name == product_name)
        rows = query.all()

        # Aggregate per winner variant type using the variants JSON
        from collections import defaultdict
        type_scores: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            # Find the winning variant's type from the variants list
            winner_idx = row.winner_variant_index
            variants = row.variants or []
            winning_variant = next(
                (v for v in variants if v.get("variant_index") == winner_idx), None
            )
            if winning_variant and row.actual_conversion_score is not None:
                vtype = winning_variant.get("variant_type")
                if vtype:
                    type_scores[vtype].append(float(row.actual_conversion_score))

        return {
            vtype
            for vtype, scores in type_scores.items()
            if scores and (sum(scores) / len(scores)) > _HISTORY_BOOST_THRESHOLD
        }
    except Exception:
        return set()

