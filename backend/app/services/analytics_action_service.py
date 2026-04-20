from __future__ import annotations

from typing import Any

from app.services.commerce.content_goal_classifier import ContentGoalClassifier
from app.services.template_intelligence import TemplateIntelligenceService

_classifier = ContentGoalClassifier()
_template_intel = TemplateIntelligenceService()

# ---------------------------------------------------------------------------
# Thresholds for "needs improvement" decisions
# ---------------------------------------------------------------------------
_HOOK_WEAK_THRESHOLD = 1          # hook_strength ≤ this → suggest hook change
_CTA_WEAK_THRESHOLD = 1           # cta_presence  ≤ this → suggest CTA change
_CLARITY_WEAK_THRESHOLD = 1       # clarity       ≤ this → suggest template change
_CONVERSION_LOW_THRESHOLD = 0.50  # overall score ≤ this → comprehensive review


class AnalyticsActionService:
    """Translates conversion score analytics into actionable suggestions.

    Input: a conversion_score dict (as produced by ConversionScoreService)
           plus optional context (goal, market, current template).

    Output: a list of ``{action, reason, suggestion}`` dicts.
    """

    def suggest(
        self,
        *,
        conversion_score: float,
        details: dict[str, Any] | None = None,
        content_goal: str | None = None,
        market_code: str | None = None,
        current_template_family: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return a prioritised list of improvement actions.

        Args:
            conversion_score: Overall score in [0, 1].
            details: Sub-scores dict from ConversionScoreService
                     (keys: hook_strength, clarity, cta_presence).
            content_goal: Current content goal string.
            market_code: Market/locale code.
            current_template_family: Currently used template family name.

        Returns:
            List of action dicts, each with keys:
              - action:     one of "change_hook" | "change_cta" | "change_template"
              - reason:     human-readable explanation
              - suggestion: concrete recommendation string
              - priority:   "high" | "medium" | "low"
        """
        details = details or {}
        actions: list[dict[str, Any]] = []

        hook_pts: int = int(details.get("hook_strength", 1))
        cta_pts: int = int(details.get("cta_presence", 1))
        clarity_pts: int = int(details.get("clarity", 1))

        # --- Hook suggestions ---
        if hook_pts <= _HOOK_WEAK_THRESHOLD:
            actions.append(
                {
                    "action": "change_hook",
                    "reason": f"Hook strength is low ({hook_pts}/3). Audience is not being grabbed fast enough.",
                    "suggestion": self._hook_suggestion(content_goal),
                    "priority": "high",
                }
            )

        # --- CTA suggestions ---
        if cta_pts <= _CTA_WEAK_THRESHOLD:
            actions.append(
                {
                    "action": "change_cta",
                    "reason": f"CTA presence is weak ({cta_pts}/4). Conversion intent is unclear.",
                    "suggestion": self._cta_suggestion(content_goal),
                    "priority": "high",
                }
            )

        # --- Template suggestions ---
        if clarity_pts <= _CLARITY_WEAK_THRESHOLD:
            actions.append(
                {
                    "action": "change_template",
                    "reason": f"Clarity score is low ({clarity_pts}/3). Scene structure may be confusing.",
                    "suggestion": self._template_suggestion(content_goal, market_code, current_template_family),
                    "priority": "medium",
                }
            )

        # --- Comprehensive suggestion for very low overall score ---
        if conversion_score <= _CONVERSION_LOW_THRESHOLD and not actions:
            actions.append(
                {
                    "action": "comprehensive_review",
                    "reason": f"Overall conversion score is low ({conversion_score:.2f}). Full script review recommended.",
                    "suggestion": (
                        "Consider rebuilding the script using the review or sales_conversion template. "
                        "Add a strong numeric hook (e.g. '3 ways…') and an urgency CTA."
                    ),
                    "priority": "high",
                }
            )

        # Sort: high → medium → low
        priority_order = {"high": 0, "medium": 1, "low": 2}
        actions.sort(key=lambda a: priority_order.get(a["priority"], 3))

        return actions

    def suggest_from_score_result(
        self,
        score_result: dict[str, Any],
        *,
        content_goal: str | None = None,
        market_code: str | None = None,
        current_template_family: str | None = None,
    ) -> list[dict[str, Any]]:
        """Convenience wrapper accepting the dict returned by ConversionScoreService."""
        return self.suggest(
            conversion_score=float(score_result.get("conversion_score", 0.0)),
            details=score_result.get("details"),
            content_goal=content_goal,
            market_code=market_code,
            current_template_family=current_template_family,
        )

    # --- Private suggestion builders ---

    def _hook_suggestion(self, content_goal: str | None) -> str:
        base = (
            "Open with a direct question or a surprising statistic. "
            "Use words like 'Did you know', 'Stop doing X', or a bold number claim."
        )
        if content_goal == "entertainment":
            return "Use a trending audio cue or shock-value visual in the first 2 seconds. " + base
        if content_goal in ("sales", "conversion"):
            return "Lead with a scarcity or discount angle. " + base
        return base

    def _cta_suggestion(self, content_goal: str | None) -> str:
        if content_goal in ("sales", "conversion"):
            return (
                "Add urgency language: 'Buy now — offer ends tonight'. "
                "Include a clear directional cue: 'link in bio', 'tap below', 'swipe up'."
            )
        if content_goal == "lead_generation":
            return "Add a low-friction CTA: 'Take the free quiz' or 'Download the checklist'."
        return (
            "Add a clear action verb (get, try, start, join) + a directional cue "
            "(link in bio, tap below) to every CTA scene."
        )

    def _template_suggestion(
        self,
        content_goal: str | None,
        market_code: str | None,
        current_family: str | None,
    ) -> str:
        intel = _template_intel.resolve(content_goal or "brand_awareness", market_code)
        recommended = intel["template_family"]
        if recommended == current_family:
            return (
                f"The template '{current_family}' is correct but execution is unclear. "
                "Break each scene to a single idea. Aim for ≤ 20 words per scene."
            )
        return (
            f"Switch from '{current_family}' to '{recommended}' template. "
            f"This template is optimised for the '{content_goal}' goal and the "
            f"'{market_code or 'global'}' market."
        )
