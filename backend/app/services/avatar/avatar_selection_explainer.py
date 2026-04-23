"""avatar_selection_explainer — generates human-readable explanations for
why a particular avatar was selected (or rejected) in a tournament.

Used by the debug API and decision engine notes.
"""
from __future__ import annotations

from typing import Any

from app.schemas.avatar_selection_debug import AvatarSelectionDebugView


class AvatarSelectionExplainer:
    """Builds debug explanations for avatar selection decisions."""

    def build(
        self,
        *,
        avatar_id: str,
        base_score: float,
        pair_bonus: float,
        continuity_bonus: float,
        governance_penalty: float,
        exploration_bonus: float,
        final_score: float,
        state: str,
        is_selected: bool = False,
        in_cooldown: bool = False,
        is_exploration: bool = False,
    ) -> AvatarSelectionDebugView:
        lines: list[str] = []

        if is_selected:
            lines.append("✓ Selected as tournament winner.")

        if state == "priority":
            lines.append("Priority avatar: elevated base weight.")
        elif state == "candidate":
            lines.append("Candidate avatar: limited outcome history.")
        elif state == "cooldown":
            lines.append("⚠ In cooldown — excluded from exploitation.")
        elif state == "blocked":
            lines.append("✗ Blocked by governance — not eligible.")

        if in_cooldown:
            lines.append("Cooldown active — only eligible for exploration slot.")

        if pair_bonus > 0:
            lines.append(f"Pair fit bonus applied: +{pair_bonus:.3f} (template × topic match).")
        if continuity_bonus > 0:
            lines.append(f"Continuity health bonus: +{continuity_bonus:.3f}.")
        if governance_penalty > 0:
            lines.append(f"Governance penalty applied: -{governance_penalty:.3f}.")
        if is_exploration:
            lines.append("Exploration slot: selected to maintain discovery quota.")

        lines.append(f"Final rank score: {final_score:.4f}.")

        return AvatarSelectionDebugView(
            avatar_id=avatar_id,
            base_score=base_score,
            pair_bonus=pair_bonus,
            continuity_bonus=continuity_bonus,
            governance_penalty=governance_penalty,
            exploration_bonus=exploration_bonus,
            final_score=final_score,
            state=state,
            explanation_lines=lines,
        )

    def build_tournament_explanation(
        self,
        *,
        selected_avatar_id: str,
        ranked_candidates: list[dict[str, Any]],
        selection_mode: str,
    ) -> dict[str, Any]:
        top = ranked_candidates[0] if ranked_candidates else {}
        return {
            "selected_avatar_id": selected_avatar_id,
            "selection_mode": selection_mode,
            "winner_score": top.get("final_rank_score", 0.0),
            "candidate_count": len(ranked_candidates),
            "ranking_summary": [
                {
                    "rank": i + 1,
                    "avatar_id": c.get("avatar_id"),
                    "final_rank_score": c.get("final_rank_score", 0.0),
                }
                for i, c in enumerate(ranked_candidates[:5])
            ],
        }
