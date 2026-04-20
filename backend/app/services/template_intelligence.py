from __future__ import annotations

# ---------------------------------------------------------------------------
# content_goal → template family mapping
# ---------------------------------------------------------------------------
_GOAL_TO_TEMPLATE_FAMILY: dict[str, str] = {
    "product_demo": "product_review",
    "brand_awareness": "brand_story",
    "lead_generation": "lead_capture",
    "education": "how_to",
    "testimonial": "testimonial",
    "entertainment": "viral_clip",
    "sales": "sales_conversion",
    "conversion": "sales_conversion",
}

# ---------------------------------------------------------------------------
# market → style preset mapping
# Covers common locale / country codes.
# ---------------------------------------------------------------------------
_MARKET_TO_STYLE_PRESET: dict[str, str] = {
    # South-east Asia
    "vi-VN": "vibrant_minimal",
    "th-TH": "vibrant_minimal",
    "id-ID": "vibrant_minimal",
    "ms-MY": "vibrant_minimal",
    "tl-PH": "vibrant_minimal",
    # East Asia
    "zh-CN": "clean_modern",
    "zh-TW": "clean_modern",
    "ja-JP": "clean_modern",
    "ko-KR": "clean_modern",
    # South Asia
    "hi-IN": "bold_expressive",
    "bn-BD": "bold_expressive",
    # English-speaking markets
    "en-US": "professional_bold",
    "en-GB": "professional_bold",
    "en-AU": "professional_bold",
    "en-CA": "professional_bold",
    # Western Europe
    "fr-FR": "elegant_minimal",
    "de-DE": "clean_modern",
    "es-ES": "vibrant_minimal",
    "it-IT": "elegant_minimal",
    "pt-PT": "vibrant_minimal",
    "pt-BR": "vibrant_minimal",
    # Middle East
    "ar-SA": "bold_expressive",
    "ar-AE": "bold_expressive",
    # Default
    "_default": "professional_bold",
}

# ---------------------------------------------------------------------------
# content_goal → recommended CTA intent
# ---------------------------------------------------------------------------
_GOAL_TO_CTA_INTENT: dict[str, str] = {
    "product_demo": "soft",
    "brand_awareness": "social_proof",
    "lead_generation": "urgency",
    "education": "soft",
    "testimonial": "social_proof",
    "entertainment": "social_proof",
    "sales": "discount",
    "conversion": "urgency",
}

# ---------------------------------------------------------------------------
# template_family → recommended scene count
# ---------------------------------------------------------------------------
_TEMPLATE_SCENE_COUNT: dict[str, int] = {
    "product_review": 6,
    "brand_story": 5,
    "lead_capture": 5,
    "how_to": 7,
    "testimonial": 5,
    "viral_clip": 4,
    "sales_conversion": 7,
}


class TemplateIntelligenceService:
    """Maps content goals and markets to template families and style presets.

    Fully heuristic — no external dependencies or DB required.
    """

    def get_template_family(self, content_goal: str) -> str:
        """Return the recommended template family name for the given goal."""
        return _GOAL_TO_TEMPLATE_FAMILY.get(content_goal, "product_review")

    def get_style_preset(self, market_code: str) -> str:
        """Return the recommended style preset for the given market/locale."""
        # Try exact match first, then language prefix (e.g. "en" from "en-XX")
        preset = _MARKET_TO_STYLE_PRESET.get(market_code)
        if preset:
            return preset
        lang_prefix = market_code.split("-")[0] if market_code else ""
        for key, value in _MARKET_TO_STYLE_PRESET.items():
            if key.startswith(lang_prefix + "-"):
                return value
        return _MARKET_TO_STYLE_PRESET["_default"]

    def get_cta_intent(self, content_goal: str) -> str:
        """Return the recommended CTA intent mode for the given goal."""
        return _GOAL_TO_CTA_INTENT.get(content_goal, "default")

    def get_recommended_scene_count(self, template_family: str) -> int:
        """Return the optimal scene count for the given template family."""
        return _TEMPLATE_SCENE_COUNT.get(template_family, 6)

    def resolve(
        self,
        content_goal: str,
        market_code: str | None = None,
    ) -> dict[str, object]:
        """Return a full intelligence bundle for a content goal + market.

        Returns a dict with keys:
          - template_family
          - style_preset
          - cta_intent
          - recommended_scene_count
        """
        template_family = self.get_template_family(content_goal)
        style_preset = self.get_style_preset(market_code or "_default")
        cta_intent = self.get_cta_intent(content_goal)
        scene_count = self.get_recommended_scene_count(template_family)
        return {
            "template_family": template_family,
            "style_preset": style_preset,
            "cta_intent": cta_intent,
            "recommended_scene_count": scene_count,
        }
