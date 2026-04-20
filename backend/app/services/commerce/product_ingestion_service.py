from __future__ import annotations

from app.schemas.product_ingestion import NormalizedProductProfile, ProductIngestionRequest


class ProductIngestionService:
    NEGATIVE_KEYWORDS = ("slow", "hard", "difficult", "expensive", "confusing", "pain")

    def ingest(self, req: ProductIngestionRequest) -> NormalizedProductProfile:
        features = [f.strip() for f in (req.product_features or []) if f and f.strip()]
        reviews = [r.strip() for r in (req.customer_reviews or []) if r and r.strip()]

        product_name = req.product_name or self._derive_name(req.product_url) or "Unknown Product"
        description = (req.product_description or "").strip()

        pain_points = self._extract_pain_points(features, reviews, description)
        benefits = self._extract_benefits(features)
        social_proof = self._extract_social_proof(reviews)

        recommended_angles = [
            "problem-solution",
            "before-after",
            "quick-demo",
        ]
        if social_proof:
            recommended_angles.append("testimonial")

        return NormalizedProductProfile(
            product_name=product_name,
            product_features=features,
            pain_points=pain_points,
            benefits=benefits,
            social_proof=social_proof,
            target_audience=req.target_audience,
            recommended_angles=recommended_angles,
            market_code=req.market_code,
            metadata={"source_type": req.source_type or ("url" if req.product_url else "direct")},
        )

    @staticmethod
    def _derive_name(product_url: str | None) -> str | None:
        if not product_url:
            return None
        slug = product_url.rstrip("/").split("/")[-1].replace("-", " ").strip()
        return slug.title() if slug else None

    def _extract_pain_points(self, features: list[str], reviews: list[str], description: str) -> list[str]:
        points: list[str] = []
        for text in [*features, *reviews, description]:
            lower = text.lower()
            if any(k in lower for k in self.NEGATIVE_KEYWORDS):
                points.append(text)
        if not points and features:
            points.append(f"Users struggle without {features[0]}")
        return points[:5]

    @staticmethod
    def _extract_benefits(features: list[str]) -> list[str]:
        if not features:
            return []
        return [f"Delivers {feature}" for feature in features[:6]]

    @staticmethod
    def _extract_social_proof(reviews: list[str]) -> list[str]:
        return [f"Customer says: {review}" for review in reviews[:3]]
