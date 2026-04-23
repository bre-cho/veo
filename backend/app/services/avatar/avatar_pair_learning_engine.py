from __future__ import annotations

from typing import Any

from app.services.avatar.avatar_pair_optimizer import AvatarPairOptimizer


class AvatarPairLearningEngine:
    def __init__(self, pair_optimizer: AvatarPairOptimizer | None = None) -> None:
        self.pair_optimizer = pair_optimizer or AvatarPairOptimizer()

    def get_pair_features(self, *, avatar_id, template_family: str | None, topic_signature: str | None, platform: str | None) -> dict[str, float]:
        return self.pair_optimizer.score_pair(
            avatar_id=avatar_id,
            template_family=template_family,
            topic_signature=topic_signature,
            platform=platform,
        )

    def ingest_outcome(self, *, avatar_id, template_family: str | None, topic_signature: str | None, platform: str | None, fitness_score: float | None) -> None:
        self.pair_optimizer.update_pair_history(
            avatar_id=avatar_id,
            template_family=template_family,
            topic_signature=topic_signature,
            platform=platform,
            fitness_score=fitness_score,
        )
