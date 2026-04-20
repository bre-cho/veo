from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_GOAL_KEYWORDS: dict[str, list[str]] = {
    "product_demo": ["demo", "showcase", "feature", "product", "launch"],
    "brand_awareness": ["brand", "awareness", "introduce", "identity"],
    "lead_generation": ["lead", "signup", "convert", "funnel", "capture"],
    "education": ["teach", "learn", "tutorial", "how to", "explain", "guide"],
    "testimonial": ["review", "testimonial", "customer", "feedback", "success story"],
    "entertainment": ["fun", "entertain", "viral", "trend", "challenge"],
    "sales": ["buy", "purchase", "offer", "discount", "sale", "promo"],
}

# Minimum records required to activate statistical detection
_STATISTICAL_MIN_RECORDS = 50


class ContentGoalClassifier:
    """Keyword-based goal classifier (legacy / fallback).

    When a DB session is provided and ≥50 performance records exist, the
    ``CategoryIntelligenceLayer`` will attempt a statistical detection first.
    """

    def classify(self, brief: str) -> str:
        brief_lower = brief.lower()
        scores: dict[str, int] = {}
        for goal, keywords in _GOAL_KEYWORDS.items():
            scores[goal] = sum(1 for kw in keywords if kw in brief_lower)
        best = max(scores, key=lambda g: scores[g])
        if scores[best] == 0:
            return "brand_awareness"
        return best

    def classify_with_confidence(
        self,
        brief: str,
        db: "Session | None" = None,
    ) -> tuple[str, float]:
        # Try statistical layer first when DB is available
        if db is not None:
            layer = CategoryIntelligenceLayer(db=db)
            goal, confidence = layer.detect(brief, product_data={})
            if confidence >= 0.6:
                return goal, confidence

        brief_lower = brief.lower()
        scores: dict[str, int] = {}
        for goal, keywords in _GOAL_KEYWORDS.items():
            scores[goal] = sum(1 for kw in keywords if kw in brief_lower)
        total = sum(scores.values())
        best = max(scores, key=lambda g: scores[g])
        if total == 0:
            return "brand_awareness", 0.5
        confidence = round(scores[best] / total, 3)
        return best, confidence


class CategoryIntelligenceLayer:
    """ML-ready abstraction for content goal / category detection.

    Chooses between ``KeywordCategoryDetector`` (always available) and
    ``StatisticalCategoryDetector`` (requires ≥50 DB records) automatically.
    """

    def __init__(self, db: "Session") -> None:
        self._db = db

    def detect(self, text: str, product_data: dict[str, Any]) -> tuple[str, float]:
        """Return (category, confidence) using the best available detector."""
        record_count = self._get_record_count()
        if record_count >= _STATISTICAL_MIN_RECORDS:
            return StatisticalCategoryDetector(self._db).detect(text, product_data)
        return KeywordCategoryDetector().detect(text, product_data)

    def _get_record_count(self) -> int:
        try:
            from app.models.performance_record import PerformanceRecord
            return self._db.query(PerformanceRecord).count()
        except Exception:
            return 0


class KeywordCategoryDetector:
    """Current keyword-matching detector (always available)."""

    def detect(self, text: str, product_data: dict[str, Any]) -> tuple[str, float]:
        text_lower = text.lower()
        scores: dict[str, int] = {}
        for goal, keywords in _GOAL_KEYWORDS.items():
            scores[goal] = sum(1 for kw in keywords if kw in text_lower)
        total = sum(scores.values())
        best = max(scores, key=lambda g: scores[g])
        if total == 0:
            return "brand_awareness", 0.5
        confidence = round(scores[best] / total, 3)
        return best, confidence


class StatisticalCategoryDetector:
    """TF-IDF inspired detector built from performance_records table.

    When ≥50 records are present it builds a goal-specific token frequency
    table and scores the input text against it.  Falls back to keyword
    detection when DB query fails.
    """

    def __init__(self, db: "Session") -> None:
        self._db = db

    def detect(self, text: str, product_data: dict[str, Any]) -> tuple[str, float]:
        try:
            from app.models.performance_record import PerformanceRecord
            rows = self._db.query(PerformanceRecord).all()
            if not rows:
                return KeywordCategoryDetector().detect(text, product_data)

            # Build per-template_family token frequency
            family_tokens: dict[str, dict[str, int]] = {}
            for row in rows:
                family = row.template_family or "unknown"
                tokens = (row.hook_pattern + " " + row.cta_pattern).lower().split()
                if family not in family_tokens:
                    family_tokens[family] = {}
                for tok in tokens:
                    family_tokens[family][tok] = family_tokens[family].get(tok, 0) + 1

            text_tokens = set(text.lower().split())
            scores: dict[str, float] = {}
            for family, freq in family_tokens.items():
                scores[family] = sum(freq.get(tok, 0) for tok in text_tokens)

            if not scores or max(scores.values()) == 0:
                return KeywordCategoryDetector().detect(text, product_data)

            best = max(scores, key=lambda g: scores[g])
            total = sum(scores.values())
            confidence = round(scores[best] / total, 3) if total > 0 else 0.5
            return best, min(confidence, 0.95)
        except Exception:
            return KeywordCategoryDetector().detect(text, product_data)

