from __future__ import annotations

_GOAL_KEYWORDS: dict[str, list[str]] = {
    "product_demo": ["demo", "showcase", "feature", "product", "launch"],
    "brand_awareness": ["brand", "awareness", "introduce", "identity"],
    "lead_generation": ["lead", "signup", "convert", "funnel", "capture"],
    "education": ["teach", "learn", "tutorial", "how to", "explain", "guide"],
    "testimonial": ["review", "testimonial", "customer", "feedback", "success story"],
    "entertainment": ["fun", "entertain", "viral", "trend", "challenge"],
    "sales": ["buy", "purchase", "offer", "discount", "sale", "promo"],
}


class ContentGoalClassifier:
    def classify(self, brief: str) -> str:
        brief_lower = brief.lower()
        scores: dict[str, int] = {}
        for goal, keywords in _GOAL_KEYWORDS.items():
            scores[goal] = sum(1 for kw in keywords if kw in brief_lower)
        best = max(scores, key=lambda g: scores[g])
        if scores[best] == 0:
            return "brand_awareness"
        return best

    def classify_with_confidence(self, brief: str) -> tuple[str, float]:
        brief_lower = brief.lower()
        scores: dict[str, int] = {}
        for goal, keywords in _GOAL_KEYWORDS.items():
            scores[goal] = sum(1 for kw in keywords if kw in brief_lower)
        total = sum(scores.values()) or 1
        best = max(scores, key=lambda g: scores[g])
        confidence = round(scores[best] / total, 3) if total > 0 else 0.5
        return best if scores[best] > 0 else "brand_awareness", confidence
