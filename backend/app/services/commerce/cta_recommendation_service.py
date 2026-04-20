from __future__ import annotations

_CTA_MAP: dict[str, dict[str, str]] = {
    "product_demo": {
        "default": "See it in action – Start your free demo",
        "urgency": "Limited spots – Claim your demo now",
        "soft": "Explore how it works →",
    },
    "brand_awareness": {
        "default": "Discover what we stand for",
        "urgency": "Join thousands who already follow us",
        "soft": "Learn our story →",
    },
    "lead_generation": {
        "default": "Get your free consultation today",
        "urgency": "Only 10 spots left – Book now",
        "soft": "See if you qualify →",
    },
    "education": {
        "default": "Start learning for free",
        "urgency": "Enroll before seats fill up",
        "soft": "Preview the curriculum →",
    },
    "entertainment": {
        "default": "Watch more & follow for weekly drops",
        "urgency": "Don't miss the next episode – Subscribe",
        "soft": "See what's trending →",
    },
    "sales": {
        "default": "Shop now – Limited time offer",
        "urgency": "Sale ends in 24 hours",
        "soft": "Browse the collection →",
    },
    "testimonial": {
        "default": "Read real customer stories",
        "urgency": "Join 10,000+ happy customers",
        "soft": "See what others are saying →",
    },
}
_DEFAULT_CTA = "Get started today"


_DEFAULT_BRIEF = "brand awareness video"


class CTARecommendationService:
    def recommend(self, content_goal: str, conversion_mode: str | None = None) -> str:
        goal_map = _CTA_MAP.get(content_goal, {})
        if not goal_map:
            return _DEFAULT_CTA
        mode = conversion_mode or "default"
        return goal_map.get(mode, goal_map.get("default", _DEFAULT_CTA))
