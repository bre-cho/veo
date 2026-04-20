from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Product category → expected conversion signal boosters
# ---------------------------------------------------------------------------
_CATEGORY_SIGNALS: dict[str, float] = {
    "skincare": 0.80,
    "fitness": 0.78,
    "food": 0.72,
    "technology": 0.75,
    "fashion": 0.76,
    "health": 0.80,
    "education": 0.74,
    "finance": 0.72,
}

# Platform-specific weight for conversion intent signals
_PLATFORM_INTENT_SIGNALS: dict[str, float] = {
    "tiktok": 0.82,
    "shorts": 0.80,
    "reels": 0.80,
    "youtube": 0.74,
    "facebook": 0.72,
    "instagram": 0.78,
}


class ConversionScoringEngine:
    def score_variant(
        self,
        variant: dict[str, Any],
        market_code: str | None = None,
        persona: str | None = None,
        product_category: str | None = None,
        platform: str | None = None,
    ) -> dict[str, Any]:
        text = " ".join(
            [
                str(variant.get("hook") or ""),
                str(variant.get("body") or ""),
                str(variant.get("cta") or ""),
            ]
        ).lower()

        hook_strength = 0.8 if any(x in text for x in ("?", "did you know", "secret", "stop")) else 0.55
        clarity = 0.75 if len(text.split()) < 120 else 0.55
        trust = 0.8 if any(x in text for x in ("customer", "review", "trusted", "proven")) else 0.6
        cta_quality = 0.85 if any(x in text for x in ("buy", "tap", "start", "claim", "order", "shop")) else 0.5
        market_fit = 0.75 if market_code else 0.65

        # New dimension: persona_fit
        persona_fit = self._score_persona_fit(text, persona)

        # New dimension: product_category_fit
        product_category_fit = self._score_category_fit(product_category)

        # New dimension: platform_fit
        platform_fit = self._score_platform_fit(text, platform)

        score = round(
            (hook_strength + clarity + trust + cta_quality + market_fit
             + persona_fit + product_category_fit + platform_fit) / 8,
            3,
        )
        return {
            "score": score,
            "details": {
                "hook_strength": round(hook_strength, 3),
                "clarity": round(clarity, 3),
                "trust": round(trust, 3),
                "cta_quality": round(cta_quality, 3),
                "market_fit": round(market_fit, 3),
                "persona_fit": round(persona_fit, 3),
                "product_category_fit": round(product_category_fit, 3),
                "platform_fit": round(platform_fit, 3),
            },
        }

    # ------------------------------------------------------------------
    # New scoring helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_persona_fit(text: str, persona: str | None) -> float:
        """Score how well the variant copy targets the intended persona."""
        if not persona:
            return 0.65  # neutral when unknown
        persona_lower = persona.lower()
        # Direct mention of persona label in copy
        if persona_lower in text:
            return 0.90
        # General persona category signals
        persona_signals = {
            "professional": ("professional", "business", "work", "team", "company"),
            "student": ("student", "learn", "study", "skill"),
            "parent": ("parent", "family", "mom", "dad", "child"),
            "entrepreneur": ("entrepreneur", "grow", "scale", "startup", "revenue"),
            "athlete": ("athlete", "fitness", "performance", "training", "results"),
        }
        for key, signals in persona_signals.items():
            if key in persona_lower:
                if any(s in text for s in signals):
                    return 0.80
        return 0.65

    @staticmethod
    def _score_category_fit(product_category: str | None) -> float:
        """Return base conversion expectation for this product category."""
        if not product_category:
            return 0.68
        return _CATEGORY_SIGNALS.get(product_category.lower(), 0.68)

    @staticmethod
    def _score_platform_fit(text: str, platform: str | None) -> float:
        """Score how well the variant's language fits the target platform."""
        if not platform:
            return 0.68
        platform_lower = platform.lower()
        base = _PLATFORM_INTENT_SIGNALS.get(platform_lower, 0.70)
        # Short-form platforms reward short punchy copy
        if platform_lower in ("tiktok", "shorts", "reels"):
            word_count = len(text.split())
            if word_count < 80:
                base = min(base + 0.05, 1.0)
            elif word_count > 150:
                base = max(base - 0.05, 0.0)
        # Long-form platforms (YouTube) reward more detailed copy
        elif platform_lower == "youtube":
            word_count = len(text.split())
            if word_count > 100:
                base = min(base + 0.04, 1.0)
        return base
