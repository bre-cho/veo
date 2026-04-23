"""template_selector — choose the best template for a given intake request.

Scoring rubric (additive, higher is better):
  +2.0  content_goal matches template.best_for.content_goal
  +1.0  market_code  matches template.best_for.market_code
  +2.0  topic_class  matches template.best_for.topic_classes
  +1.0  episode_role is escalation/continuation AND template narrative is
        reveal_escalation or story_escalation
  +0.5  winner_dna hook_core is present (bias toward known winners)

Default fallback (no positive match at all): story_chain_retention
"""
from __future__ import annotations

from typing import Any

from app.schemas.template_system import TemplateSelectionResult
from app.services.template.template_registry import TEMPLATE_REGISTRY

_FALLBACK_TEMPLATE_ID = "story_chain_retention"

_ESCALATION_NARRATIVE_MODES = {"reveal_escalation", "story_escalation"}
_ESCALATION_EPISODE_ROLES = {"escalation", "continuation"}

_TOPIC_KEYWORD_MAP: dict[str, str] = {
    "ai": "ai",
    "algorithm": "ai",
    "automation": "ai",
    "machine": "ai",
    "control": "control",
    "attention": "control",
    "system": "control",
    "hidden": "control",
    "war": "war",
    "conflict": "war",
    "secret": "war",
    "collapse": "war",
    "scandal": "war",
    "story": "documentary",
    "life": "documentary",
    "biography": "documentary",
    "journey": "documentary",
    "mystery": "documentary",
}


class TemplateSelector:
    def _classify_topic(self, request: dict[str, Any]) -> str:
        raw = (request.get("topic") or request.get("script_text") or "").lower()
        for keyword, topic_class in _TOPIC_KEYWORD_MAP.items():
            if keyword in raw:
                return topic_class
        return "system"

    def select(
        self,
        *,
        request: dict[str, Any],
        memory_bundle: dict[str, Any],
        continuity: dict[str, Any],
    ) -> TemplateSelectionResult:
        topic_class = self._classify_topic(request)
        content_goal = request.get("content_goal")
        market_code = request.get("market_code")
        episode_role = continuity.get("episode_role")

        best_score = -1.0
        best_template_id = _FALLBACK_TEMPLATE_ID
        best_reasons: list[str] = []

        for template_id, template in TEMPLATE_REGISTRY.items():
            score = 0.0
            local_reasons: list[str] = []

            if content_goal and content_goal in template.best_for.content_goal:
                score += 2.0
                local_reasons.append("content_goal_match")

            if market_code and market_code in template.best_for.market_code:
                score += 1.0
                local_reasons.append("market_match")

            if topic_class in template.best_for.topic_classes:
                score += 2.0
                local_reasons.append("topic_class_match")

            if (
                episode_role in _ESCALATION_EPISODE_ROLES
                and template.narrative_mode in _ESCALATION_NARRATIVE_MODES
            ):
                score += 1.0
                local_reasons.append("episode_role_match")

            winner_dna = memory_bundle.get("winner_dna_summary") or {}
            if isinstance(winner_dna, dict) and winner_dna.get("hook_core") and template.hook_strategy:
                score += 0.5
                local_reasons.append("winner_dna_bias")

            if score > best_score:
                best_score = score
                best_template_id = template_id
                best_reasons = local_reasons

        chosen = TEMPLATE_REGISTRY[best_template_id]
        return TemplateSelectionResult(
            template_id=chosen.template_id,
            template_family=chosen.template_family,
            score=best_score,
            reasons=best_reasons,
            template_payload=chosen.model_dump(),
        )
