from __future__ import annotations

from app.schemas.avatar_selection_debug import AvatarSelectionDebugView


class AvatarSelectionExplainer:
    def build_debug_view(self, *, avatar_id, base_score: float, pair_bonus: float, continuity_bonus: float, exploration_bonus: float, governance_penalty: float, final_score: float, state: str) -> AvatarSelectionDebugView:
        lines: list[str] = []
        lines.append(f"base_score={base_score:.4f}")
        if pair_bonus:
            lines.append(f"pair_bonus=+{pair_bonus:.4f}")
        if continuity_bonus:
            lines.append(f"continuity_bonus=+{continuity_bonus:.4f}")
        if exploration_bonus:
            lines.append(f"exploration_bonus=+{exploration_bonus:.4f}")
        if governance_penalty:
            lines.append(f"governance_penalty=-{governance_penalty:.4f}")
        lines.append(f"state={state}")
        return AvatarSelectionDebugView(
            avatar_id=avatar_id,
            base_score=base_score,
            pair_bonus=pair_bonus,
            continuity_bonus=continuity_bonus,
            exploration_bonus=exploration_bonus,
            governance_penalty=governance_penalty,
            final_score=final_score,
            state=state,
            explanation_lines=lines,
        )
