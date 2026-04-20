from __future__ import annotations

from typing import Any


class ConversionScoringEngine:
    def score_variant(self, variant: dict[str, Any], market_code: str | None = None) -> dict[str, Any]:
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

        score = round((hook_strength + clarity + trust + cta_quality + market_fit) / 5, 3)
        return {
            "score": score,
            "details": {
                "hook_strength": round(hook_strength, 3),
                "clarity": round(clarity, 3),
                "trust": round(trust, 3),
                "cta_quality": round(cta_quality, 3),
                "market_fit": round(market_fit, 3),
            },
        }
