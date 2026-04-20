from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.autovis import TemplateFamily
from app.repositories.localization_repo import LocalizationRepo
from app.services.commerce.conversion_scoring_engine import ConversionScoringEngine

_loc_repo = LocalizationRepo()
_scoring_engine = ConversionScoringEngine()


class TemplateRecommendationService:
    def recommend(
        self,
        db: Session,
        avatar_id: str,
        content_goal: str,
        limit: int = 5,
        product_profile: dict | None = None,
        platform: str | None = None,
    ) -> list[dict]:
        """Recommend templates with optional product-profile enrichment.

        When ``product_profile`` is supplied, each candidate template family
        is re-ranked by combining the stored fit_score with a heuristic
        conversion signal derived from the new scoring dimensions
        (persona_fit, product_category_fit, platform_fit).
        """
        # Find template fits for this avatar
        fits = _loc_repo.list_template_fits(db, avatar_id)
        if fits:
            results = []
            for fit in fits[:limit * 2]:
                family = db.query(TemplateFamily).filter(TemplateFamily.id == fit.template_family_id).first()
                if family and family.is_active:
                    base_score = float(fit.fit_score or 0)
                    boosted_score = self._boost_score(
                        base_score,
                        family=family,
                        product_profile=product_profile,
                        content_goal=content_goal,
                        platform=platform,
                    )
                    results.append({
                        "template_family_id": family.id,
                        "name": family.name,
                        "content_goal": family.content_goal,
                        "fit_score": round(boosted_score, 4),
                        "base_fit_score": base_score,
                    })
            if results:
                results.sort(key=lambda r: r["fit_score"], reverse=True)
                return results[:limit]

        # Fall back to content_goal based
        families = (
            db.query(TemplateFamily)
            .filter(
                TemplateFamily.is_active.is_(True),
                TemplateFamily.content_goal == content_goal,
            )
            .limit(limit * 2)
            .all()
        )
        results = []
        for f in families:
            boosted = self._boost_score(
                0.0,
                family=f,
                product_profile=product_profile,
                content_goal=content_goal,
                platform=platform,
            )
            results.append({
                "template_family_id": f.id,
                "name": f.name,
                "content_goal": f.content_goal,
                "fit_score": round(boosted, 4) if boosted > 0 else None,
                "base_fit_score": None,
            })
        results.sort(key=lambda r: r.get("fit_score") or 0, reverse=True)
        return results[:limit]

    def _boost_score(
        self,
        base: float,
        *,
        family: TemplateFamily,
        product_profile: dict | None,
        content_goal: str,
        platform: str | None,
    ) -> float:
        """Apply product-profile scoring boost to a template candidate score."""
        if product_profile is None:
            return base

        # Build a minimal variant dict to reuse ConversionScoringEngine signals
        stub_variant = {
            "hook": " ".join(product_profile.get("pain_points") or [])[:100],
            "body": " ".join(product_profile.get("benefits") or [])[:150],
            "cta": "Shop now",
        }
        scored = _scoring_engine.score_variant(
            stub_variant,
            market_code=product_profile.get("market_code"),
            persona=(product_profile.get("personas") or [None])[0],
            product_category=product_profile.get("product_category"),
            platform=platform,
        )
        conversion_signal = scored["score"]

        # Blend: 60% base fit + 40% product conversion signal
        if base > 0:
            return round(base * 0.6 + conversion_signal * 0.4, 4)
        # No stored fit score – return conversion signal as proxy
        return round(conversion_signal * 0.4, 4)
