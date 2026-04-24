from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence


@dataclass
class RecallCandidate:
    memory: object
    score: float


class MemoryRecallEngine:
    """Ranks stored drama memories for a given trigger.

    Current implementation is heuristic and intentionally simple so the
    persistence / API layer can stabilize before a learned retrieval model is used.
    """

    TRIGGER_BOOST_WEIGHT = 0.45
    PERSISTENCE_WEIGHT = 0.35
    EMOTIONAL_WEIGHT = 0.20

    def recall(self, memories: Sequence[object], trigger: str, limit: int = 10) -> List[object]:
        normalized_trigger = (trigger or "").strip().lower()
        scored: List[RecallCandidate] = []
        for memory in memories:
            score = self._score_memory(memory, normalized_trigger)
            scored.append(RecallCandidate(memory=memory, score=score))

        scored.sort(key=lambda item: item.score, reverse=True)
        return [item.memory for item in scored[:limit]]

    def _score_memory(self, memory: object, trigger: str) -> float:
        recall_trigger = getattr(memory, "recall_trigger", "") or ""
        meaning_label = getattr(memory, "meaning_label", "") or ""
        persistence_score = float(getattr(memory, "persistence_score", 0.0) or 0.0)
        emotional_weight = float(getattr(memory, "emotional_weight", 0.0) or 0.0)

        text = f"{recall_trigger} {meaning_label}".lower()
        trigger_match = 1.0 if trigger and trigger in text else 0.0

        return (
            trigger_match * self.TRIGGER_BOOST_WEIGHT
            + persistence_score * self.PERSISTENCE_WEIGHT
            + min(emotional_weight, 1.0) * self.EMOTIONAL_WEIGHT
        )
