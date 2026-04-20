from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.services.commerce.content_goal_classifier import ContentGoalClassifier
from app.services.commerce.cta_recommendation_service import CTARecommendationService
from app.services.commerce.product_ingestion_service import ProductIngestionService
from app.services.commerce.review_variant_engine import ReviewVariantEngine
from app.services.script_ingestion import build_subtitle_segments_from_scenes, estimate_duration

_classifier = ContentGoalClassifier()
_cta_svc = CTARecommendationService()

# ---------------------------------------------------------------------------
# Scene roles for a review-style video
# ---------------------------------------------------------------------------
_SCENE_ROLES = ("hook", "pain", "solution", "benefit", "social_proof", "cta")

# Words / patterns that signal high hook strength
_HOOK_STRENGTH_PATTERNS = [
    r"\?",           # question mark
    r"\b\d+\b",      # number (stats, quantities)
    r"\b(secret|hack|mistake|never|always|finally|warning|stop|start)\b",
    r"\b(you|your)\b",  # direct address
    r"!",            # exclamation
]

# Conversion-intent signals for CTA scoring
_CTA_SIGNALS = [
    r"\b(get|buy|shop|order|download|sign up|join|start|claim|grab|try|book|schedule)\b",
    r"\b(now|today|free|limited|exclusive|instantly|fast)\b",
    r"\b(link|bio|below|click|tap|swipe)\b",
    r"→|✓|👇|🔥",
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ReviewVideoScene:
    scene_index: int
    scene_role: str
    title: str
    script_text: str
    visual_prompt: str
    target_duration_sec: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_index": self.scene_index,
            "scene_role": self.scene_role,
            "title": self.title,
            "script_text": self.script_text,
            "visual_prompt": self.visual_prompt,
            "target_duration_sec": self.target_duration_sec,
            "metadata": self.metadata,
        }


@dataclass
class ReviewVideoScript:
    product_name: str
    target_audience: str
    content_goal: str
    conversion_mode: str | None
    hook: str
    body: str
    cta: str
    scenes: list[ReviewVideoScene]
    conversion_score: float = 0.0

    def to_preview_payload(
        self,
        aspect_ratio: str = "9:16",
        target_platform: str = "shorts",
        avatar_id: str | None = None,
        market_code: str | None = None,
    ) -> dict[str, Any]:
        raw_scenes = [s.to_dict() for s in self.scenes]
        subtitles = build_subtitle_segments_from_scenes(raw_scenes)
        full_script = "\n\n".join(s.script_text for s in self.scenes)
        return {
            "avatar_id": avatar_id,
            "market_code": market_code,
            "content_goal": self.content_goal,
            "conversion_mode": self.conversion_mode,
            "source_mode": "script_upload",
            "aspect_ratio": aspect_ratio,
            "target_platform": target_platform,
            "style_preset": None,
            "original_filename": None,
            "script_text": full_script,
            "scenes": raw_scenes,
            "subtitle_segments": subtitles,
        }


# ---------------------------------------------------------------------------
# Conversion Score service
# ---------------------------------------------------------------------------

class ConversionScoreService:
    """Heuristic conversion score for a review video script.

    Returns a float in [0, 1] from three pillars:
      • hook_strength  (0–3 pts)
      • clarity        (0–3 pts)
      • cta_presence   (0–4 pts)

    Max = 10 pts → score = total / 10.
    """

    MAX_SCORE = 10

    def score_script(self, script: ReviewVideoScript) -> dict[str, Any]:
        hook_pts = self._score_hook(script.hook, script.scenes)
        clarity_pts = self._score_clarity(script.scenes)
        cta_pts = self._score_cta(script.cta, script.scenes)
        total = hook_pts + clarity_pts + cta_pts
        conversion_score = round(total / self.MAX_SCORE, 3)
        return {
            "conversion_score": conversion_score,
            "details": {
                "hook_strength": hook_pts,
                "clarity": clarity_pts,
                "cta_presence": cta_pts,
                "max_possible": self.MAX_SCORE,
            },
        }

    def score_scenes(self, scenes: list[dict[str, Any]], cta_text: str = "") -> dict[str, Any]:
        hook_text = ""
        for s in scenes:
            if s.get("scene_role") == "hook" or s.get("scene_index") == 1:
                hook_text = s.get("script_text") or ""
                break
        hook_pts = self._score_hook_text(hook_text)
        clarity_pts = self._score_clarity_dicts(scenes)
        cta_pts = self._score_cta_text(cta_text) + self._score_cta_in_scenes(scenes)
        cta_pts = min(cta_pts, 4)
        total = hook_pts + clarity_pts + cta_pts
        conversion_score = round(total / self.MAX_SCORE, 3)
        return {
            "conversion_score": conversion_score,
            "details": {
                "hook_strength": hook_pts,
                "clarity": clarity_pts,
                "cta_presence": cta_pts,
                "max_possible": self.MAX_SCORE,
            },
        }

    # --- Hook scoring ---

    def _score_hook(self, hook: str, scenes: list[ReviewVideoScene]) -> int:
        hook_scene_text = hook
        for s in scenes:
            if s.scene_role == "hook":
                hook_scene_text = s.script_text
                break
        return self._score_hook_text(hook_scene_text or hook)

    def _score_hook_text(self, text: str) -> int:
        pts = 0
        text_lower = (text or "").lower()
        matched = sum(
            1 for pat in _HOOK_STRENGTH_PATTERNS if re.search(pat, text_lower)
        )
        if matched >= 3:
            pts = 3
        elif matched >= 2:
            pts = 2
        elif matched >= 1:
            pts = 1
        return pts

    # --- Clarity scoring ---

    def _score_clarity(self, scenes: list[ReviewVideoScene]) -> int:
        return self._score_clarity_dicts([s.to_dict() for s in scenes])

    def _score_clarity_dicts(self, scenes: list[dict[str, Any]]) -> int:
        pts = 0
        if not scenes:
            return pts
        texts = [s.get("script_text") or "" for s in scenes]
        avg_words = sum(len(t.split()) for t in texts) / len(texts)

        # Each scene should be concise (5–30 words ideal for short-form)
        if 5 <= avg_words <= 30:
            pts += 2
        elif avg_words < 50:
            pts += 1

        # Presence of scene roles suggests structured narrative
        roles = {s.get("scene_role") for s in scenes if s.get("scene_role")}
        if len(roles) >= 3:
            pts += 1

        return min(pts, 3)

    # --- CTA scoring ---

    def _score_cta(self, cta: str, scenes: list[ReviewVideoScene]) -> int:
        pts = self._score_cta_text(cta)
        pts += self._score_cta_in_scenes([s.to_dict() for s in scenes])
        return min(pts, 4)

    def _score_cta_text(self, text: str) -> int:
        if not text:
            return 0
        text_lower = text.lower()
        matched = sum(1 for pat in _CTA_SIGNALS if re.search(pat, text_lower))
        return min(matched, 3)

    def _score_cta_in_scenes(self, scenes: list[dict[str, Any]]) -> int:
        for s in scenes:
            if s.get("scene_role") == "cta":
                return 1
        return 0


# ---------------------------------------------------------------------------
# Review Video Engine
# ---------------------------------------------------------------------------

class ReviewVideoEngine:
    """Generates a review-style video script from product information.

    Scene structure (5–7 scenes):
      1. HOOK        – punchy question / shocking stat (0–5 s)
      2. PAIN        – describe the audience's pain point
      3. SOLUTION    – introduce the product as the fix
      4. BENEFIT     – primary feature-benefit pair
      5. BENEFIT 2   – secondary feature (optional, included when ≥2 features)
      6. SOCIAL PROOF– who's already using it / credibility signal
      7. CTA         – explicit call-to-action with urgency or value
    """

    def __init__(self) -> None:
        self._score_svc = ConversionScoreService()
        self._product_ingestion = ProductIngestionService()
        self._review_variant_engine = ReviewVariantEngine()

    def generate(
        self,
        *,
        product_name: str,
        product_features: list[str],
        target_audience: str,
        conversion_mode: str | None = None,
        market_code: str | None = None,
        avatar_id: str | None = None,
    ) -> ReviewVideoScript:
        product_brief = (
            f"product review {product_name} for {target_audience}. "
            f"Features: {', '.join(product_features)}"
        )
        content_goal = _classifier.classify(product_brief)
        cta_text = _cta_svc.recommend(content_goal, conversion_mode)

        features = [f.strip() for f in product_features if f.strip()]
        feature_1 = features[0] if features else "its core capability"
        feature_2 = features[1] if len(features) > 1 else None

        hook = self._build_hook(product_name, target_audience, features)
        pain = self._build_pain(target_audience, features)
        solution = self._build_solution(product_name, target_audience)
        benefit_1 = self._build_benefit(product_name, feature_1)
        benefit_2 = self._build_benefit(product_name, feature_2) if feature_2 else None
        social_proof = self._build_social_proof(product_name)
        cta_scene = self._build_cta_scene(product_name, cta_text)

        scenes_data: list[tuple[str, str, str]] = [
            ("hook", "Hook", hook),
            ("pain", "The Problem", pain),
            ("solution", "The Solution", solution),
            ("benefit", f"Why {product_name}", benefit_1),
        ]
        if benefit_2:
            scenes_data.append(("benefit", f"More From {product_name}", benefit_2))
        scenes_data.append(("social_proof", "Trusted By Many", social_proof))
        scenes_data.append(("cta", "Get Started", cta_scene))

        scenes: list[ReviewVideoScene] = []
        for idx, (role, title, text) in enumerate(scenes_data, start=1):
            visual_prompt = self._build_visual_prompt(role, product_name, target_audience, text)
            scenes.append(
                ReviewVideoScene(
                    scene_index=idx,
                    scene_role=role,
                    title=title,
                    script_text=text,
                    visual_prompt=visual_prompt,
                    target_duration_sec=estimate_duration(text),
                    metadata={"scene_role": role},
                )
            )

        body = f"{pain}\n\n{solution}\n\n{benefit_1}"
        if benefit_2:
            body += f"\n\n{benefit_2}"

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
        score_result = self._score_svc.score_script(script)
        script.conversion_score = score_result["conversion_score"]
        return script

    # --- Scene text builders ---

    def _build_hook(self, product_name: str, audience: str, features: list[str]) -> str:
        pain_hint = features[0] if features else "your biggest challenge"
        return (
            f"Struggling with {pain_hint}? "
            f"If you're a {audience}, {product_name} might be exactly what you've been waiting for."
        )

    def _build_pain(self, audience: str, features: list[str]) -> str:
        pain = features[0] if features else "productivity"
        return (
            f"Most {audience}s face the same problem every day: "
            f"{pain} that wastes time and slows them down. "
            f"Sound familiar?"
        )

    def _build_solution(self, product_name: str, audience: str) -> str:
        return (
            f"That's exactly why {product_name} was built — "
            f"specifically for {audience}s who need results fast."
        )

    def _build_benefit(self, product_name: str, feature: str) -> str:
        return (
            f"With {product_name}, you get {feature} — "
            f"so you can focus on what matters most."
        )

    def _build_social_proof(self, product_name: str) -> str:
        return (
            f"Thousands of users already trust {product_name} to get the job done. "
            f"Real results. Real people."
        )

    def _build_cta_scene(self, product_name: str, cta_text: str) -> str:
        return (
            f"Ready to transform your workflow? "
            f"Get {product_name} today. {cta_text}."
        )

    def _build_visual_prompt(
        self,
        role: str,
        product_name: str,
        audience: str,
        script_text: str,
    ) -> str:
        role_hints = {
            "hook": f"eye-catching opening, {audience} looking frustrated or curious",
            "pain": f"relatable struggle scene for {audience}",
            "solution": f"clean product reveal of {product_name}, confident presenter",
            "benefit": f"product in use, {audience} achieving results",
            "social_proof": f"montage of happy users, testimonial-style visuals",
            "cta": f"strong call-to-action frame, {product_name} logo, clear text overlay",
        }
        hint = role_hints.get(role, f"scene for {product_name}")
        return f"{hint}. {script_text[:80].strip()}"

    # ------------------------------------------------------------------
    # V2 variant orchestration
    # ------------------------------------------------------------------

    def generate_review_variants(
        self,
        *,
        product_payload: dict[str, Any],
        variant_count: int = 5,
    ) -> dict[str, Any]:
        if product_payload.get("benefits") is not None and product_payload.get("pain_points") is not None:
            profile = dict(product_payload)
        else:
            profile = self._product_ingestion.ingest(
                req=self._build_product_ingestion_request(product_payload)
            ).model_dump()
        variants = self._review_variant_engine.generate_variants(profile, count=variant_count)
        winner = self._review_variant_engine.select_winner(variants)
        return {
            "normalized_product_profile": profile,
            "variants": variants,
            "winner": winner,
        }

    def select_review_winner(self, variants: list[dict[str, Any]]) -> dict[str, Any]:
        return self._review_variant_engine.select_winner(variants)

    @staticmethod
    def _build_product_ingestion_request(product_payload: dict[str, Any]):
        from app.schemas.product_ingestion import ProductIngestionRequest

        return ProductIngestionRequest(
            product_url=product_payload.get("product_url"),
            product_name=product_payload.get("product_name"),
            product_features=product_payload.get("product_features"),
            product_description=product_payload.get("product_description"),
            customer_reviews=product_payload.get("customer_reviews"),
            target_audience=product_payload.get("target_audience"),
            market_code=product_payload.get("market_code"),
            source_type=product_payload.get("source_type"),
        )
