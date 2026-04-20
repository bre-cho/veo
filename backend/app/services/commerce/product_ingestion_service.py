from __future__ import annotations

from app.schemas.product_ingestion import NormalizedProductProfile, ProductIngestionRequest

# ---------------------------------------------------------------------------
# Category classification keywords
# ---------------------------------------------------------------------------
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "skincare": ["skin", "cream", "serum", "moisturizer", "cleanser", "toner", "face", "acne"],
    "fitness": ["workout", "gym", "exercise", "weight", "muscle", "protein", "training"],
    "food": ["eat", "drink", "recipe", "meal", "food", "snack", "taste", "flavor"],
    "technology": ["app", "software", "tech", "digital", "ai", "data", "platform", "tool", "cloud"],
    "fashion": ["wear", "style", "outfit", "clothes", "fashion", "shirt", "dress", "pants"],
    "health": ["health", "wellness", "vitamin", "supplement", "medical", "doctor", "mental"],
    "education": ["learn", "course", "study", "skill", "knowledge", "training", "tutor"],
    "finance": ["money", "invest", "save", "finance", "budget", "income", "profit", "revenue"],
}

_OBJECTION_KEYWORDS = (
    "too expensive", "too costly", "not sure", "doubt", "worried", "skeptical",
    "doesn't work", "waste", "scam", "risky", "don't need", "complicated",
)

_PERSONA_KEYWORDS = {
    "busy professional": ("professional", "office", "work", "manager", "executive", "business"),
    "student": ("student", "learn", "study", "school", "college", "university"),
    "parent": ("parent", "mom", "dad", "family", "child", "kids"),
    "entrepreneur": ("entrepreneur", "startup", "founder", "owner", "freelancer", "creator"),
    "athlete": ("athlete", "fitness", "gym", "sport", "runner", "training"),
}


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

        # New: extract personas and objections (use provided if available)
        personas = req.personas if req.personas else self._extract_personas(
            features, reviews, description, req.target_audience
        )
        objections = req.objections if req.objections else self._extract_objections(reviews, description)

        # New: detect product category (use provided if available)
        product_category = req.product_category or self._detect_category(
            product_name, features, description
        )

        recommended_angles = [
            "problem-solution",
            "before-after",
            "quick-demo",
        ]
        if social_proof:
            recommended_angles.append("testimonial")
        if personas:
            recommended_angles.append("persona-focus")
        if objections:
            recommended_angles.append("objection-handling")

        return NormalizedProductProfile(
            product_name=product_name,
            product_features=features,
            pain_points=pain_points,
            benefits=benefits,
            social_proof=social_proof,
            personas=personas,
            objections=objections,
            product_category=product_category,
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

    @staticmethod
    def _extract_personas(
        features: list[str],
        reviews: list[str],
        description: str,
        target_audience: str | None,
    ) -> list[str]:
        """Infer likely buyer personas from product context."""
        combined = " ".join([*features, *reviews, description, target_audience or ""]).lower()
        found: list[str] = []
        for persona, keywords in _PERSONA_KEYWORDS.items():
            if any(kw in combined for kw in keywords):
                found.append(persona)
        # Fall back to audience as a single persona if nothing detected
        if not found and target_audience:
            found = [target_audience]
        return found[:4]

    @staticmethod
    def _extract_objections(reviews: list[str], description: str) -> list[str]:
        """Extract common buyer objections from reviews and product description."""
        combined = " ".join([*reviews, description]).lower()
        found: list[str] = []
        for objection in _OBJECTION_KEYWORDS:
            if objection in combined:
                found.append(objection)
        return found[:4]

    @staticmethod
    def _detect_category(
        product_name: str,
        features: list[str],
        description: str,
    ) -> str | None:
        """Detect the primary product category from name/features/description."""
        combined = " ".join([product_name, *features, description]).lower()
        best_category: str | None = None
        best_count = 0
        for category, keywords in _CATEGORY_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in combined)
            if count > best_count:
                best_count = count
                best_category = category
        return best_category if best_count >= 2 else None
