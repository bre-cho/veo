"""template_ab_service — lightweight A/B variant picker for the Brain Layer.

A/B selection happens at decision / project-creation time, NOT inside the
render worker.  The rule is simple:
  - If there is no recent winner (cold-start) → always run A/B.
  - If the best template score is below the confidence threshold → run A/B.
  - Otherwise, commit to the primary template.
"""
from __future__ import annotations

from typing import Any

from app.services.template.template_registry import TEMPLATE_REGISTRY

_AB_SCORE_THRESHOLD = 3.5  # run A/B when primary score < this


class TemplateABService:
    def should_run_ab(
        self,
        *,
        primary_score: float,
        has_recent_winner: bool,
    ) -> bool:
        """Return True when A/B testing should be activated."""
        if not has_recent_winner:
            return True
        return primary_score < _AB_SCORE_THRESHOLD

    def choose_secondary_template(self, *, primary_template_id: str) -> str | None:
        """Return the first registry template that is not the primary."""
        for template_id in TEMPLATE_REGISTRY:
            if template_id != primary_template_id:
                return template_id
        return None

    def pick_variants(
        self,
        *,
        primary_template_id: str,
        secondary_template_id: str | None = None,
        # legacy kwarg alias kept for backward compat
        fallback_template_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return 1 or 2 variant dicts.

        Variant A is always the primary.  Variant B is added when a distinct
        secondary (or fallback) is provided.
        """
        secondary = secondary_template_id or fallback_template_id
        variants: list[dict[str, Any]] = []

        primary = TEMPLATE_REGISTRY.get(primary_template_id)
        if primary:
            variants.append(
                {
                    "variant_id": "A",
                    "template_id": primary.template_id,
                    "template_payload": primary.model_dump(),
                }
            )

        if secondary and secondary != primary_template_id:
            sec = TEMPLATE_REGISTRY.get(secondary)
            if sec:
                variants.append(
                    {
                        "variant_id": "B",
                        "template_id": sec.template_id,
                        "template_payload": sec.model_dump(),
                    }
                )

        return variants
