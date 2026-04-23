"""template_mutation_engine — produce a mutated variant of a winner template.

Mutation only touches execution DNA (hook pacing, CTA style, prompt bias
contrast).  The template_family and core narrative mode are preserved so the
mutant remains within its content-goal niche.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4


class TemplateMutationEngine:
    def mutate(self, *, template_payload: dict[str, Any]) -> dict[str, Any]:
        """Return a deep-copy of *template_payload* with small mutations applied."""
        mutated = deepcopy(template_payload)

        # Increase hook pacing slightly (cap at 2.5)
        pacing = mutated.get("pacing_profile") or {}
        if "hook" in pacing:
            pacing["hook"] = round(min(float(pacing["hook"]) + 0.2, 2.5), 2)
            mutated["pacing_profile"] = pacing

        # Rotate CTA style between two high-retention options
        if mutated.get("cta_style") == "series_open_loop":
            mutated["cta_style"] = "curiosity_cliffhanger"
        else:
            mutated["cta_style"] = "series_open_loop"

        # Nudge contrast bias to the next intensity level
        prompt_bias = mutated.get("prompt_bias") or {}
        if isinstance(prompt_bias, dict):
            prompt_bias["contrast"] = (
                "very_high" if prompt_bias.get("contrast") != "very_high" else "high"
            )
            mutated["prompt_bias"] = prompt_bias

        # Tag the new template with a unique ID and origin metadata
        base_id = mutated.get("template_id") or "unknown"
        mutated["template_id"] = f"{base_id}_mut_{uuid4().hex[:6]}"
        metadata = mutated.setdefault("metadata", {})
        metadata["origin_type"] = "mutation"
        metadata["parent_template_id"] = base_id

        return mutated
