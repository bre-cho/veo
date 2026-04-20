"""ProductPerformanceModel — aggregate product/persona performance from learning store."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from app.models.product_learning_snapshot import ProductLearningSnapshot

if TYPE_CHECKING:
    from app.services.learning_engine import PerformanceLearningEngine

_SNAPSHOT_MIN_SAMPLE = 3


class ProductPerformanceModel:
    """Aggregates product+persona performance data from the learning store.

    Uses ``PerformanceLearningEngine.top_hook_patterns()`` / ``top_cta_patterns()``
    filtered to the given ``product_id`` and optionally ``persona_id`` (mapped
    to ``avatar_id`` in the learning records).
    """

    def aggregate(
        self,
        db: Session,
        learning_store: "PerformanceLearningEngine",
        product_id: str,
        persona_id: str | None = None,
    ) -> dict[str, Any]:
        """Return aggregated performance summary for a product+persona combination."""
        top_hooks = learning_store.top_hook_patterns(
            product_id=product_id,
            persona_id=persona_id,
        )
        top_ctas = learning_store.top_cta_patterns(
            product_id=product_id,
            persona_id=persona_id,
        )
        summary = learning_store.feedback_summary(
            product_id=product_id,
            persona_id=persona_id,
        )
        return {
            "product_id": product_id,
            "persona_id": persona_id,
            "top_hook_patterns": top_hooks,
            "top_cta_patterns": top_ctas,
            "avg_conversion": summary.get("avg_conversion_score", 0.0),
            "sample_count": summary.get("total_records", 0),
        }

    def take_snapshot(
        self,
        db: Session,
        learning_store: "PerformanceLearningEngine",
        product_id: str,
        persona_id: str | None = None,
    ) -> ProductLearningSnapshot | None:
        """Persist a learning snapshot; guard: only write if sample_count >= 3.

        Returns the persisted ``ProductLearningSnapshot`` row, or None when the
        sample guard is not met.
        """
        data = self.aggregate(db, learning_store, product_id, persona_id=persona_id)
        sample_count: int = data.get("sample_count", 0)
        if sample_count < _SNAPSHOT_MIN_SAMPLE:
            return None

        top_hooks: list[dict[str, Any]] = data.get("top_hook_patterns", [])
        top_ctas: list[dict[str, Any]] = data.get("top_cta_patterns", [])
        top_hook_style = top_hooks[0]["pattern"] if top_hooks else None
        top_cta_style = top_ctas[0]["pattern"] if top_ctas else None

        snapshot = ProductLearningSnapshot(
            product_id=product_id,
            persona_id=persona_id,
            top_hook_style=top_hook_style,
            top_cta_style=top_cta_style,
            avg_conversion=data.get("avg_conversion"),
            sample_count=sample_count,
            aggregated_data=data,
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot
