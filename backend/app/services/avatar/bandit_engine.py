"""bandit_engine — Thompson-sampling bandit for avatar × template_family arm selection."""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.avatar_bandit_state import AvatarBanditState
from app.schemas.avatar_learning import BanditArmState


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class BanditEngine:
    """Implements Thompson sampling over (avatar_id, template_family) arms.

    Each arm has a Beta(alpha, beta) distribution.  At selection time a sample
    is drawn from this distribution; higher samples indicate higher expected
    reward.  After observing a reward the distribution parameters are updated.

    Reward should be in [0, 1].
    """

    def sample(
        self,
        db: Session,
        *,
        avatar_id: str,
        template_family: str,
    ) -> float:
        """Draw a Thompson sample for the given arm.  Returns a value in [0, 1]."""
        arm = self._get_or_create(db, avatar_id=avatar_id, template_family=template_family)
        return random.betavariate(arm.alpha, arm.beta)

    def update(
        self,
        db: Session,
        *,
        avatar_id: str,
        template_family: str,
        reward: float,
    ) -> BanditArmState:
        """Update arm parameters with the observed *reward* ∈ [0, 1]."""
        reward = max(0.0, min(1.0, reward))
        arm = self._get_or_create(db, avatar_id=avatar_id, template_family=template_family)

        arm.pulls += 1
        arm.reward_sum += reward
        arm.alpha += reward
        arm.beta += 1 - reward
        arm.updated_at = _now()

        db.commit()
        return self._to_state(arm)

    def get_state(
        self,
        db: Session,
        *,
        avatar_id: str,
        template_family: str,
    ) -> BanditArmState | None:
        arm = (
            db.query(AvatarBanditState)
            .filter(
                AvatarBanditState.avatar_id == avatar_id,
                AvatarBanditState.template_family == template_family,
            )
            .one_or_none()
        )
        if arm is None:
            return None
        return self._to_state(arm)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_or_create(
        self,
        db: Session,
        *,
        avatar_id: str,
        template_family: str,
    ) -> AvatarBanditState:
        arm = (
            db.query(AvatarBanditState)
            .filter(
                AvatarBanditState.avatar_id == avatar_id,
                AvatarBanditState.template_family == template_family,
            )
            .one_or_none()
        )
        if arm is None:
            arm = AvatarBanditState(
                avatar_id=avatar_id,
                template_family=template_family,
            )
            db.add(arm)
            db.commit()
        return arm

    @staticmethod
    def _to_state(arm: AvatarBanditState) -> BanditArmState:
        mean = arm.alpha / (arm.alpha + arm.beta) if (arm.alpha + arm.beta) > 0 else 0.5
        return BanditArmState(
            avatar_id=arm.avatar_id,
            template_family=arm.template_family,
            pulls=arm.pulls,
            alpha=arm.alpha,
            beta=arm.beta,
            mean_reward=mean,
        )
