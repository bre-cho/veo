from __future__ import annotations

import time
import uuid
from typing import Any

from app.services.commerce.conversion_scoring_engine import ConversionScoringEngine
from app.services.storyboard_engine import StoryboardEngine

# In-memory history store for variant runs (keyed by product_name for demo;
# a real system would use a database row or cache).
_VARIANT_HISTORY: list[dict[str, Any]] = []
_MAX_HISTORY = 200


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
            payload["score"] = scored["score"]
            payload["score_breakdown"] = scored["details"]
            variants.append(payload)

        return variants

    @staticmethod
    def select_winner(variants: list[dict[str, Any]]) -> dict[str, Any]:
        if not variants:
            return {}
        return sorted(variants, key=lambda v: float(v.get("score") or 0), reverse=True)[0]

    def generate_variants_with_history(
        self,
        product_profile: dict[str, Any],
        count: int = 5,
        *,
        platform: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate variants, select winner, and persist run to in-memory history."""
        run_id = str(uuid.uuid4())
        variants = self.generate_variants(
            product_profile,
            count=count,
            platform=platform,
            context=context,
        )
        winner = self.select_winner(variants)

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
        _VARIANT_HISTORY.append(record)
        # Trim history to prevent unbounded growth
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
    ) -> list[dict[str, Any]]:
        """Return recent variant history, optionally filtered."""
        records = list(reversed(_VARIANT_HISTORY))
        if product_name:
            records = [r for r in records if r.get("product_name") == product_name]
        if platform:
            records = [r for r in records if r.get("platform") == platform]
        return records[:limit]
