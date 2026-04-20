from __future__ import annotations

# ---------------------------------------------------------------------------
# Hook templates per video template type
# ---------------------------------------------------------------------------

# Each entry is a list of hook patterns.
# Placeholders:  {product}   → product name
#                {audience}  → target audience
#                {pain}      → first feature/pain hint
#                {stat}      → optional statistic string (default "9 out of 10")
_HOOK_TEMPLATES: dict[str, list[str]] = {
    "review": [
        "Struggling with {pain}? I tried {product} so you don't have to.",
        "Is {product} really worth it for {audience}s? Let's find out.",
        "I tested {product} for 30 days — here's what happened.",
        "What nobody tells you about {product}.",
        "{stat} {audience}s wish they'd found {product} sooner.",
    ],
    "testimonial": [
        "I used to struggle with {pain} — then I found {product}.",
        "Here's how {product} changed everything for me as a {audience}.",
        "My honest experience using {product} every single day.",
        "Before {product}, {pain} was killing my productivity.",
        "Real talk: {product} did exactly what it promised.",
    ],
    "comparison": [
        "{product} vs the competition — which one wins?",
        "We tested 5 tools for {audience}s. {product} surprised us.",
        "Stop wasting money — here's the only {pain} tool that actually works.",
        "The honest comparison nobody wanted to do: {product} vs alternatives.",
        "Is {product} really better? We put it to the test.",
    ],
    "viral": [
        "POV: you finally fix {pain} in under 60 seconds 🔥",
        "This {product} trick changed everything — and it's free.",
        "Nobody talks about this {product} feature. You need to see it.",
        "Stop scrolling — this {product} hack is too good.",
        "The {audience} hack that went viral last week? It's {product}.",
    ],
    "educational": [
        "Did you know most {audience}s are doing {pain} wrong?",
        "The {pain} mistake that's costing {audience}s thousands.",
        "3 things every {audience} should know about {pain}.",
        "Why {pain} is harder than you think — and how {product} fixes it.",
        "Everything you need to know about {pain} in under 90 seconds.",
    ],
}

_DEFAULT_HOOKS: list[str] = [
    "Struggling with {pain}? {product} was built for {audience}s like you.",
    "What if you could solve {pain} in minutes? Meet {product}.",
    "{product}: the {pain} solution {audience}s have been waiting for.",
]


class HookEngine:
    """Generates hook text variations for a given template type.

    All templates are string-based heuristics — no external dependencies.
    """

    def generate(
        self,
        *,
        template_type: str,
        product_name: str,
        pain_hint: str,
        target_audience: str,
        stat: str = "9 out of 10",
        variant_index: int = 0,
    ) -> str:
        """Return a single hook string for the given template type.

        Args:
            template_type: One of ``review``, ``testimonial``, ``comparison``,
                ``viral``, ``educational``.  Falls back to default if unknown.
            product_name: Product / brand name.
            pain_hint: Short description of the pain point / main feature.
            target_audience: Target audience label (e.g. ``freelancer``).
            stat: Optional statistic (default "9 out of 10").
            variant_index: Which template variant to use (cycles via modulo).
        """
        hooks = _HOOK_TEMPLATES.get(template_type, _DEFAULT_HOOKS)
        template = hooks[variant_index % len(hooks)]
        return template.format(
            product=product_name,
            audience=target_audience,
            pain=pain_hint,
            stat=stat,
        )

    def generate_all(
        self,
        *,
        template_type: str,
        product_name: str,
        pain_hint: str,
        target_audience: str,
        stat: str = "9 out of 10",
    ) -> list[str]:
        """Return every hook variant for the given template type."""
        hooks = _HOOK_TEMPLATES.get(template_type, _DEFAULT_HOOKS)
        return [
            h.format(
                product=product_name,
                audience=target_audience,
                pain=pain_hint,
                stat=stat,
            )
            for h in hooks
        ]

    @staticmethod
    def supported_template_types() -> list[str]:
        return list(_HOOK_TEMPLATES.keys())
