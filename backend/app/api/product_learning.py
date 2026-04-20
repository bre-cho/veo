"""Product learning snapshot API endpoint."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.learning_engine import PerformanceLearningEngine
from app.services.product_performance_model import ProductPerformanceModel

router = APIRouter(prefix="/api/v1/commerce/products", tags=["commerce"])


class LearningSnapshotResponse(BaseModel):
    product_id: str
    persona_id: str | None = None
    top_hook_style: str | None = None
    top_cta_style: str | None = None
    avg_conversion: float | None = None
    sample_count: int = 0
    snapshotted_at: str | None = None
    aggregated_data: dict[str, Any] | None = None
    snapshot_written: bool = False


@router.get("/{product_id}/learning-snapshot", response_model=LearningSnapshotResponse)
def get_learning_snapshot(
    product_id: str,
    persona_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> LearningSnapshotResponse:
    """Return (or create) a learning snapshot for a product/persona combo."""
    # Check for existing snapshot first
    from app.models.product_learning_snapshot import ProductLearningSnapshot

    query = db.query(ProductLearningSnapshot).filter(
        ProductLearningSnapshot.product_id == product_id
    )
    if persona_id:
        query = query.filter(ProductLearningSnapshot.persona_id == persona_id)
    existing = query.order_by(ProductLearningSnapshot.snapshotted_at.desc()).first()

    learning_store = PerformanceLearningEngine()
    model = ProductPerformanceModel()

    # Attempt to write a fresh snapshot
    snapshot = model.take_snapshot(db, learning_store, product_id, persona_id=persona_id)
    snapshot_written = snapshot is not None
    chosen = snapshot or existing

    if chosen is None:
        # Not enough data — return aggregated view without snapshot
        data = model.aggregate(db, learning_store, product_id, persona_id=persona_id)
        return LearningSnapshotResponse(
            product_id=product_id,
            persona_id=persona_id,
            avg_conversion=data.get("avg_conversion"),
            sample_count=data.get("sample_count", 0),
            snapshot_written=False,
        )

    return LearningSnapshotResponse(
        product_id=product_id,
        persona_id=chosen.persona_id,
        top_hook_style=chosen.top_hook_style,
        top_cta_style=chosen.top_cta_style,
        avg_conversion=chosen.avg_conversion,
        sample_count=chosen.sample_count,
        snapshotted_at=chosen.snapshotted_at.isoformat() if chosen.snapshotted_at else None,
        aggregated_data=chosen.aggregated_data,
        snapshot_written=snapshot_written,
    )
