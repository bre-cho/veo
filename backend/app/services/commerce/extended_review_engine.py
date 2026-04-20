from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.commerce.content_goal_classifier import ContentGoalClassifier
from app.services.commerce.cta_engine import CTAEngine
from app.services.commerce.hook_engine import HookEngine
from app.services.commerce.review_engine import (
    ConversionScoreService,
    ReviewVideoEngine,
    ReviewVideoScene,
    ReviewVideoScript,
)
from app.services.script_ingestion import build_subtitle_segments_from_scenes, estimate_duration
from app.services.template_intelligence import TemplateIntelligenceService

_classifier = ContentGoalClassifier()
_hook_engine = HookEngine()
_cta_engine = CTAEngine()
_template_intel = TemplateIntelligenceService()

# ---------------------------------------------------------------------------
# Testimonial Video Engine
# ---------------------------------------------------------------------------


class TestimonialVideoEngine:
    """Generates a first-person testimonial-style video script."""

    def __init__(self) -> None:
        self._score_svc = ConversionScoreService()

    def generate(
        self,
        *,
        product_name: str,
        product_features: list[str],
        target_audience: str,
        conversion_mode: str | None = None,
        market_code: str | None = None,
        avatar_id: str | None = None,
        hook_variant: int = 0,
    ) -> ReviewVideoScript:
        content_goal = "testimonial"
        intel = _template_intel.resolve(content_goal, market_code)
        cta_intent = conversion_mode or intel["cta_intent"]
        features = [f.strip() for f in product_features if f.strip()]
        pain_hint = features[0] if features else "productivity"

        hook = _hook_engine.generate(
            template_type="testimonial",
            product_name=product_name,
            pain_hint=pain_hint,
            target_audience=target_audience,
            variant_index=hook_variant,
        )
        cta_text = _cta_engine.generate(
            intent=str(cta_intent),
            product_name=product_name,
            target_audience=target_audience,
        )

        scenes_data = [
            ("hook", "My Story Begins", hook),
            ("pain", "The Struggle", self._build_before(target_audience, pain_hint)),
            ("solution", "The Discovery", self._build_discovery(product_name)),
            ("benefit", "What Changed", self._build_change(product_name, features)),
            ("social_proof", "My Results", self._build_results(product_name)),
            ("cta", "You Should Try It", self._build_cta(product_name, cta_text)),
        ]

        scenes: list[ReviewVideoScene] = []
        for idx, (role, title, text) in enumerate(scenes_data, start=1):
            scenes.append(
                ReviewVideoScene(
                    scene_index=idx,
                    scene_role=role,
                    title=title,
                    script_text=text,
                    visual_prompt=self._visual_prompt(role, product_name, target_audience, text),
                    target_duration_sec=estimate_duration(text),
                    metadata={"scene_role": role, "template": "testimonial"},
                )
            )

        body = "\n\n".join(s.script_text for s in scenes[1:-1])
        script = ReviewVideoScript(
            product_name=product_name,
            target_audience=target_audience,
            content_goal=content_goal,
            conversion_mode=conversion_mode,
            hook=hook,
            body=body,
            cta=cta_text,
            scenes=scenes,
        )
        result = self._score_svc.score_script(script)
        script.conversion_score = result["conversion_score"]
        return script

    # -- text builders --

    def _build_before(self, audience: str, pain: str) -> str:
        return (
            f"I used to struggle with {pain} every single day. "
            f"As a {audience}, I thought that's just how it was."
        )

    def _build_discovery(self, product: str) -> str:
        return (
            f"Then a friend told me about {product}. "
            f"I was skeptical at first — but I gave it a shot."
        )

    def _build_change(self, product: str, features: list[str]) -> str:
        feat = features[0] if features else "its approach"
        return (
            f"The first thing that blew me away was {feat}. "
            f"{product} just works — exactly the way I needed it to."
        )

    def _build_results(self, product: str) -> str:
        return (
            f"Three months in and I can't imagine going back. "
            f"{product} saved me hours every week. Real results, no hype."
        )

    def _build_cta(self, product: str, cta_text: str) -> str:
        return f"If you're on the fence — just try it. {cta_text}"

    def _visual_prompt(self, role: str, product: str, audience: str, text: str) -> str:
        hints = {
            "hook": f"close-up face shot, {audience} speaking directly to camera",
            "pain": f"relatable struggle, {audience} looking frustrated",
            "solution": f"moment of discovery, product box / app on screen",
            "benefit": f"{product} in use, happy {audience}",
            "social_proof": f"results montage, before-after split screen",
            "cta": f"direct address, {product} logo, CTA text overlay",
        }
        hint = hints.get(role, f"scene for {product}")
        return f"{hint}. {text[:80].strip()}"


# ---------------------------------------------------------------------------
# Comparison Video Engine
# ---------------------------------------------------------------------------


class ComparisonVideoEngine:
    """Generates a head-to-head comparison video script (product vs. alternatives)."""

    def __init__(self) -> None:
        self._score_svc = ConversionScoreService()

    def generate(
        self,
        *,
        product_name: str,
        competitor_name: str,
        product_features: list[str],
        target_audience: str,
        conversion_mode: str | None = None,
        market_code: str | None = None,
        avatar_id: str | None = None,
        hook_variant: int = 0,
    ) -> ReviewVideoScript:
        content_goal = "product_demo"
        intel = _template_intel.resolve(content_goal, market_code)
        cta_intent = conversion_mode or intel["cta_intent"]
        features = [f.strip() for f in product_features if f.strip()]
        pain_hint = features[0] if features else "the job"

        hook = _hook_engine.generate(
            template_type="comparison",
            product_name=product_name,
            pain_hint=pain_hint,
            target_audience=target_audience,
            variant_index=hook_variant,
        )
        cta_text = _cta_engine.generate(
            intent=str(cta_intent),
            product_name=product_name,
            target_audience=target_audience,
        )

        scenes_data = [
            ("hook", "The Question", hook),
            ("build_tension", "The Old Way", self._build_competitor(competitor_name, pain_hint)),
            ("reveal", "Meet the Challenger", self._build_intro(product_name, target_audience)),
        ]
        for i, feat in enumerate(features[:3], start=1):
            scenes_data.append(
                ("benefit", f"Round {i}: {feat[:30]}", self._build_round(product_name, competitor_name, feat))
            )
        scenes_data.append(("social_proof", "The Verdict", self._build_verdict(product_name, competitor_name)))
        scenes_data.append(("cta", "Make the Switch", self._build_cta(product_name, cta_text)))

        scenes: list[ReviewVideoScene] = []
        for idx, (role, title, text) in enumerate(scenes_data, start=1):
            scenes.append(
                ReviewVideoScene(
                    scene_index=idx,
                    scene_role=role,
                    title=title,
                    script_text=text,
                    visual_prompt=self._visual_prompt(role, product_name, target_audience, text),
                    target_duration_sec=estimate_duration(text),
                    metadata={"scene_role": role, "template": "comparison"},
                )
            )

        body = "\n\n".join(s.script_text for s in scenes[1:-1])
        script = ReviewVideoScript(
            product_name=product_name,
            target_audience=target_audience,
            content_goal=content_goal,
            conversion_mode=conversion_mode,
            hook=hook,
            body=body,
            cta=cta_text,
            scenes=scenes,
        )
        result = self._score_svc.score_script(script)
        script.conversion_score = result["conversion_score"]
        return script

    # -- text builders --

    def _build_competitor(self, competitor: str, pain: str) -> str:
        return (
            f"{competitor} has been the go-to for {pain}. "
            f"But is it still the best option in {str(__import__('datetime').date.today().year)}?"
        )

    def _build_intro(self, product: str, audience: str) -> str:
        return (
            f"Enter {product} — specifically built for {audience}s "
            f"who want better results with less friction."
        )

    def _build_round(self, product: str, competitor: str, feature: str) -> str:
        return (
            f"On {feature}: {product} delivers a noticeably smoother experience. "
            f"{competitor} requires extra steps — {product} handles it automatically."
        )

    def _build_verdict(self, product: str, competitor: str) -> str:
        return (
            f"Bottom line: {product} wins on speed, simplicity, and value. "
            f"{competitor} is fine — but {product} is built for today."
        )

    def _build_cta(self, product: str, cta_text: str) -> str:
        return f"Ready to make the switch? {cta_text}"

    def _visual_prompt(self, role: str, product: str, audience: str, text: str) -> str:
        hints = {
            "hook": f"split-screen setup, two products side by side",
            "build_tension": f"competitor UI with friction points highlighted",
            "reveal": f"clean {product} reveal, confident brand shot",
            "benefit": f"side-by-side feature comparison, {product} winning",
            "social_proof": f"winner podium visual, {product} logo prominent",
            "cta": f"CTA screen, {product} logo, call-to-action text overlay",
        }
        hint = hints.get(role, f"comparison scene for {product}")
        return f"{hint}. {text[:80].strip()}"
