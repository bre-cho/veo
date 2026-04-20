from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.commerce.content_goal_classifier import ContentGoalClassifier
from app.services.commerce.cta_recommendation_service import CTARecommendationService
from app.services.commerce.review_engine import ConversionScoreService
from app.services.template_intelligence import TemplateIntelligenceService

_classifier = ContentGoalClassifier()
_cta_svc = CTARecommendationService()
_template_intel = TemplateIntelligenceService()
_score_svc = ConversionScoreService()


@dataclass
class ComboRecommendation:
    """Best avatar + template + CTA combination for a given brief."""

    avatar_id: str | None
    avatar_name: str | None
    template_family: str
    cta_intent: str
    style_preset: str
    recommended_scene_count: int
    estimated_conversion_score: float
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "avatar_id": self.avatar_id,
            "avatar_name": self.avatar_name,
            "template_family": self.template_family,
            "cta_intent": self.cta_intent,
            "style_preset": self.style_preset,
            "recommended_scene_count": self.recommended_scene_count,
            "estimated_conversion_score": self.estimated_conversion_score,
            "rationale": self.rationale,
        }


class AvatarTemplateComboRecommender:
    """Recommends the best avatar + template + CTA combination for a brief.

    Works fully offline (heuristic scoring) but can accept an optional list of
    candidate avatars from the DB layer to rank against.

    Scoring model (10 pts):
      - template_family alignment with content_goal  (0–4 pts)
      - cta_intent match with conversion_mode        (0–3 pts)
      - market style compatibility                   (0–3 pts)
    """

    MAX_SCORE = 10

    def recommend(
        self,
        *,
        content_goal: str,
        market_code: str | None = None,
        conversion_mode: str | None = None,
        candidate_avatars: list[dict[str, Any]] | None = None,
    ) -> ComboRecommendation:
        intel = _template_intel.resolve(content_goal, market_code)
        template_family: str = str(intel["template_family"])
        style_preset: str = str(intel["style_preset"])
        scene_count: int = int(str(intel["recommended_scene_count"]))

        # CTA intent: prefer explicit conversion_mode, fallback to intel
        effective_cta_intent = conversion_mode or str(intel["cta_intent"])

        # Score
        template_pts = self._score_template(content_goal, template_family)
        cta_pts = self._score_cta(conversion_mode, str(intel["cta_intent"]))
        market_pts = self._score_market(market_code)
        total = template_pts + cta_pts + market_pts
        estimated_score = round(total / self.MAX_SCORE, 3)

        # Best avatar selection (prefer market-matching avatar)
        best_avatar_id: str | None = None
        best_avatar_name: str | None = None
        if candidate_avatars:
            for av in candidate_avatars:
                if av.get("market_code") == market_code:
                    best_avatar_id = av.get("id")
                    best_avatar_name = av.get("name")
                    break
            if not best_avatar_id and candidate_avatars:
                best_avatar_id = candidate_avatars[0].get("id")
                best_avatar_name = candidate_avatars[0].get("name")

        rationale = (
            f"Template '{template_family}' aligns with goal '{content_goal}'. "
            f"CTA intent '{effective_cta_intent}' targets conversion mode. "
            f"Style preset '{style_preset}' suits market '{market_code or 'global'}'."
        )

        return ComboRecommendation(
            avatar_id=best_avatar_id,
            avatar_name=best_avatar_name,
            template_family=template_family,
            cta_intent=effective_cta_intent,
            style_preset=style_preset,
            recommended_scene_count=scene_count,
            estimated_conversion_score=estimated_score,
            rationale=rationale,
        )

    # --- Scoring helpers ---

    def _score_template(self, goal: str, family: str) -> int:
        # Award full points when the resolved family clearly matches a
        # sales-oriented goal; partial points otherwise.
        high_conversion = {"sales_conversion", "lead_capture", "product_review"}
        if family in high_conversion and goal in ("sales", "conversion", "lead_generation", "product_demo"):
            return 4
        if family in high_conversion:
            return 3
        return 2

    def _score_cta(self, conversion_mode: str | None, intel_intent: str) -> int:
        if not conversion_mode:
            return 2  # neutral
        if conversion_mode == intel_intent:
            return 3
        # Non-matching but explicit intent still worth something
        return 2

    def _score_market(self, market_code: str | None) -> int:
        if not market_code:
            return 1
        # Award full points for any explicit market code
        return 3
