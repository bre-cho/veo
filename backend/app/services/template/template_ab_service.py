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
    def pick_variants(
        self,
        *,
        primary_template_id: str,
        fallback_template_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return 1 or 2 variant dicts.

        Variant A is always the primary.  Variant B is added when a distinct
        fallback is provided.
        """
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

        if fallback_template_id and fallback_template_id != primary_template_id:
            secondary = TEMPLATE_REGISTRY.get(fallback_template_id)
            if secondary:
                variants.append(
                    {
                        "variant_id": "B",
                        "template_id": secondary.template_id,
                        "template_payload": secondary.model_dump(),
                    }
                )

        return variants

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
