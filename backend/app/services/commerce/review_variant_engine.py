from __future__ import annotations

from typing import Any

from app.services.commerce.conversion_scoring_engine import ConversionScoringEngine
from app.services.storyboard_engine import StoryboardEngine


class ReviewVariantEngine:
    VARIANT_TYPES = ("review", "testimonial", "comparison")

    def __init__(self) -> None:
        self._scorer = ConversionScoringEngine()
        self._storyboard = StoryboardEngine()

    def generate_variants(
        self,
        product_profile: dict[str, Any],
        count: int = 5,
    ) -> list[dict[str, Any]]:
        name = product_profile.get("product_name") or "Product"
        audience = product_profile.get("target_audience") or "customers"
        benefits = product_profile.get("benefits") or []
        pain_points = product_profile.get("pain_points") or []
        social_proof = product_profile.get("social_proof") or []

        variants: list[dict[str, Any]] = []
        for idx in range(max(3, min(count, 5))):
            variant_type = self.VARIANT_TYPES[idx % len(self.VARIANT_TYPES)]
            hook = f"{audience.title()}, are you still dealing with {pain_points[0] if pain_points else 'old workflows'}?"
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
            scored = self._scorer.score_variant(payload, market_code=product_profile.get("market_code"))
            payload["score"] = scored["score"]
            payload["score_breakdown"] = scored["details"]
            variants.append(payload)

        return variants

    @staticmethod
    def select_winner(variants: list[dict[str, Any]]) -> dict[str, Any]:
        if not variants:
            return {}
        return sorted(variants, key=lambda v: float(v.get("score") or 0), reverse=True)[0]
