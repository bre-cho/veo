"""healing_action_executor — applies healing actions (rollback, switch, cooldown)."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


class HealingActionExecutor:
    """Executes healing actions determined by :class:`SelfHealingEngine`.

    Each method returns a result dict describing what was done.
    """

    def __init__(self) -> None:
        pass

    def rollback(
        self,
        db: Session,
        *,
        avatar_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Roll back the avatar to the previous stable state via
        :class:`AvatarRollbackService`.
        """
        try:
            from app.services.avatar.avatar_rollback_service import AvatarRollbackService
            rollback_svc = AvatarRollbackService()
            new_state = rollback_svc.rollback(
                db,
                avatar_id=avatar_id,
                from_state=context.get("current_state", "active"),
                reason_code="self_healing_rollback",
                source_metrics=context.get("metrics") or {},
            )
            return {"action": "rollback", "avatar_id": avatar_id, "new_state": new_state}
        except Exception as exc:
            return {"action": "rollback", "avatar_id": avatar_id, "error": str(exc)}

    def switch_avatar(
        self,
        db: Session,
        *,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Run a new tournament with elevated exploration ratio to switch avatars."""
        try:
            from app.schemas.avatar_tournament import AvatarTournamentRequest
            from app.services.avatar.avatar_tournament_engine import AvatarTournamentEngine

            candidate_ids = context.get("candidate_avatar_ids") or []
            if not candidate_ids:
                return {"action": "switch_avatar", "error": "no_candidates"}

            req = AvatarTournamentRequest(
                workspace_id=context.get("workspace_id") or "default",
                project_id=context.get("project_id"),
                market_code=context.get("market_code"),
                content_goal=context.get("content_goal"),
                topic_class=context.get("topic_class"),
                platform=context.get("platform"),
                candidate_avatar_ids=candidate_ids,
                exploration_ratio=0.5,  # high exploration on healing
                force_avatar_ids=[],
            )
            result = AvatarTournamentEngine().run_tournament(db=db, request=req)
            return {
                "action": "switch_avatar",
                "to": str(result.selected_avatar_id),
                "tournament_run_id": result.tournament_run_id,
                "selection_mode": result.selection_mode,
            }
        except Exception as exc:
            return {"action": "switch_avatar", "error": str(exc)}

    def cooldown(
        self,
        db: Session,
        *,
        avatar_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Put the avatar into cooldown state."""
        try:
            from app.services.avatar.avatar_rollback_service import AvatarRollbackService
            rollback_svc = AvatarRollbackService()
            new_state = rollback_svc.cooldown(
                db,
                avatar_id=avatar_id,
                from_state=context.get("current_state", "active"),
                reason_code="self_healing_cooldown",
                source_metrics=context.get("metrics") or {},
            )
            return {"action": "cooldown", "avatar_id": avatar_id, "new_state": new_state}
        except Exception as exc:
            return {"action": "cooldown", "avatar_id": avatar_id, "error": str(exc)}
