"""template_evolution_engine — orchestrate template mutation and crossover.

Called after publish scoring when a winner template is identified.  The engine
reads the top-1 and top-2 winner templates (by score, same market+goal niche)
and produces:

  * 1 mutant  (from winner[0])
  * 1 crossover (from winner[0] + winner[1])   — only if 2+ winners available

Both candidates are persisted via TemplateCandidateStore with status="candidate".
They enter the selector only after being promoted (status="promoted") via a
future evaluation pass.

Trigger rule (caller responsibility)
-------------------------------------
Invoke evolve_from_winners() when:
  - template tier == "winner" (total_score >= 85) AND score >= 90  →  high priority
  - template tier == "winner" AND 85 <= score < 90                 →  mutation only
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.template.template_candidate_store import TemplateCandidateStore
from app.services.template.template_crossover_engine import TemplateCrossoverEngine
from app.services.template.template_mutation_engine import TemplateMutationEngine


class TemplateEvolutionEngine:
    def __init__(self) -> None:
        self._mutation = TemplateMutationEngine()
        self._crossover = TemplateCrossoverEngine()
        self._store = TemplateCandidateStore()

    def evolve_from_winners(
        self,
        db: Session,
        *,
        winner_templates: list[dict[str, Any]],
        market_code: str | None,
        content_goal: str | None,
        source_id: str | None,
        allow_crossover: bool = True,
    ) -> list[dict[str, Any]]:
        """Produce and persist evolution candidates from *winner_templates*.

        Parameters
        ----------
        winner_templates:
            Ordered list of winner template payloads (highest score first).
            At least one entry is required; a second enables crossover.
        allow_crossover:
            When False only mutation is performed (e.g. score 85–89).

        Returns
        -------
        List of generated candidate dicts (unsaved copies, already written to DB).
        """
        candidates: list[dict[str, Any]] = []
        if not winner_templates:
            return candidates

        primary = winner_templates[0]

        # Always mutate the top winner
        mutated = self._mutation.mutate(template_payload=primary)
        candidates.append(mutated)

        # Crossover if we have a second winner and it is allowed
        if allow_crossover and len(winner_templates) > 1:
            secondary = winner_templates[1]
            crossed = self._crossover.crossover(
                primary_template=primary,
                secondary_template=secondary,
            )
            candidates.append(crossed)

        for candidate in candidates:
            self._store.save_candidate(
                db,
                candidate_payload=candidate,
                market_code=market_code,
                content_goal=content_goal,
                source_id=source_id,
            )

        return candidates
