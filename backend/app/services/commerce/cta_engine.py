from __future__ import annotations

# ---------------------------------------------------------------------------
# CTA templates organised by intent mode
# ---------------------------------------------------------------------------
# Placeholders:
#   {product}   → product name
#   {audience}  → target audience
#   {discount}  → discount string (e.g. "20% off")
#   {deadline}  → deadline hint   (e.g. "this weekend only")

_CTA_TEMPLATES: dict[str, list[str]] = {
    "urgency": [
        "Get {product} now — offer ends {deadline}! 🔥",
        "Only a few spots left. Claim yours before it's gone → {product}",
        "{deadline} only: try {product} free and lock in the discount.",
        "Don't wait — {product} prices go up after {deadline}.",
        "Last chance for {audience}s: grab {product} at this rate today.",
    ],
    "discount": [
        "Use code SAVE to get {discount} off {product} today.",
        "{discount} off {product} — this week only. Link in bio 👇",
        "Right now: {product} is {discount} off for first-time buyers.",
        "Stack your savings: {discount} on {product} + free shipping.",
        "New to {product}? Use code NEW for {discount} off your first order.",
    ],
    "social_proof": [
        "Join 10,000+ {audience}s already using {product}.",
        "Rated #1 by {audience}s for 3 years running — try {product} free.",
        "See why {audience}s call {product} their secret weapon. 👉 Link below.",
        "Over 50,000 five-star reviews. {product} speaks for itself.",
        "The {audience} community agrees: {product} is worth every penny.",
    ],
    "soft": [
        "Curious? Explore {product} at no risk → link in bio.",
        "Start your free {product} trial today — no credit card needed.",
        "See if {product} is right for you → take the 2-minute quiz.",
        "Discover {product} and decide for yourself. Zero pressure.",
        "Try {product} free for 14 days. Cancel anytime.",
    ],
    "default": [
        "Get {product} today and start seeing results.",
        "Try {product} now — built specifically for {audience}s.",
        "Ready to level up? {product} is the move.",
        "Start with {product} today. Your future self will thank you.",
        "{product}: the upgrade every {audience} deserves.",
    ],
}


class CTAEngine:
    """Advanced CTA generator supporting urgency, discount, social-proof,
    soft, and default intent modes.

    All text is produced from string templates — no external dependencies.
    """

    def generate(
        self,
        *,
        intent: str,
        product_name: str,
        target_audience: str,
        discount: str = "20% off",
        deadline: str = "midnight tonight",
        variant_index: int = 0,
    ) -> str:
        """Return a single CTA string.

        Args:
            intent: One of ``urgency``, ``discount``, ``social_proof``,
                ``soft``, ``default``.
            product_name: Product / brand name.
            target_audience: Target audience label.
            discount: Discount text (used when intent is ``discount``).
            deadline: Deadline text (used when intent is ``urgency``).
            variant_index: Which variant to pick (cycles via modulo).
        """
        templates = _CTA_TEMPLATES.get(intent, _CTA_TEMPLATES["default"])
        template = templates[variant_index % len(templates)]
        return template.format(
            product=product_name,
            audience=target_audience,
            discount=discount,
            deadline=deadline,
        )

    def generate_all(
        self,
        *,
        intent: str,
        product_name: str,
        target_audience: str,
        discount: str = "20% off",
        deadline: str = "midnight tonight",
    ) -> list[str]:
        """Return all CTA variants for the given intent."""
        templates = _CTA_TEMPLATES.get(intent, _CTA_TEMPLATES["default"])
        return [
            t.format(
                product=product_name,
                audience=target_audience,
                discount=discount,
                deadline=deadline,
            )
            for t in templates
        ]

    def generate_bundle(
        self,
        *,
        product_name: str,
        target_audience: str,
        discount: str = "20% off",
        deadline: str = "midnight tonight",
    ) -> dict[str, str]:
        """Return one CTA per intent mode — useful for A/B test bundles."""
        return {
            intent: self.generate(
                intent=intent,
                product_name=product_name,
                target_audience=target_audience,
                discount=discount,
                deadline=deadline,
                variant_index=0,
            )
            for intent in _CTA_TEMPLATES
        }

    @staticmethod
    def supported_intents() -> list[str]:
        return list(_CTA_TEMPLATES.keys())
