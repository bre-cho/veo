"""template_crossover_engine — combine two winner templates into a hybrid.

The primary template supplies structure (narrative mode, pacing base).
The secondary template donates its hook_strategy, CTA style, first-two scene
beats, and prompt_bias to inject novel execution into the primary's frame.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4


class TemplateCrossoverEngine:
    def crossover(
        self,
        *,
        primary_template: dict[str, Any],
        secondary_template: dict[str, Any],
    ) -> dict[str, Any]:
        """Return a new template that blends *primary* and *secondary*."""
        result = deepcopy(primary_template)

        # Borrow hook strategy from secondary
        secondary_hook = secondary_template.get("hook_strategy")
        if secondary_hook:
            result["hook_strategy"] = secondary_hook

        # Borrow CTA style from secondary
        secondary_cta = secondary_template.get("cta_style")
        if secondary_cta:
            result["cta_style"] = secondary_cta

        # Splice first 2 scene beats from secondary into primary sequence
        secondary_sequence = secondary_template.get("scene_sequence") or []
        if secondary_sequence:
            primary_sequence = result.get("scene_sequence") or []
            result["scene_sequence"] = secondary_sequence[:2] + primary_sequence[2:]

        # Adopt secondary prompt_bias wholesale (richer signal)
        secondary_bias = secondary_template.get("prompt_bias") or {}
        if secondary_bias:
            result["prompt_bias"] = deepcopy(secondary_bias)

        # Build unique ID and track lineage
        primary_id = primary_template.get("template_id") or "primary"
        secondary_id = secondary_template.get("template_id") or "secondary"
        result["template_id"] = f"{primary_id}_x_{secondary_id}_{uuid4().hex[:6]}"
        metadata = result.setdefault("metadata", {})
        metadata["origin_type"] = "crossover"
        metadata["parent_template_ids"] = [primary_id, secondary_id]

        return result
