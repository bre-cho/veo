"""Experiment variant management API endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.variant_history_service import VariantHistoryService

router = APIRouter(prefix="/api/v1/commerce/experiments", tags=["commerce"])


class VariantSummary(BaseModel):
    id: str
    run_id: str
    product_name: str | None = None
    platform: str | None = None
    winner_variant_index: int | None = None
    winner_score: float | None = None
    actual_conversion_score: float | None = None
    actual_ctr: float | None = None
    context: dict[str, Any] | None = None


class WinnerResponse(BaseModel):
    ok: bool
    experiment_id: str
    winner_id: str | None = None
    winner_score: float | None = None
    weight_profile: dict[str, Any] = Field(default_factory=dict)


class OutcomeResponse(BaseModel):
    ok: bool
    variant_id: str
    actual_conversion_score: float | None = None
    actual_ctr: float | None = None
    outcome_recorded_at: str | None = None
    context: dict[str, Any] | None = None


_svc = VariantHistoryService()


@router.get("/{experiment_id}/variants", response_model=list[VariantSummary])
def list_variants(
    experiment_id: str,
    db: Session = Depends(get_db),
) -> list[VariantSummary]:
    """List all variant run records for an experiment, sorted by conversion rate."""
    rows = _svc.list_variants(db, experiment_id)
    return [
        VariantSummary(
            id=r.id,
            run_id=r.run_id,
            product_name=r.product_name,
            platform=r.platform,
            winner_variant_index=r.winner_variant_index,
            winner_score=r.winner_score,
            actual_conversion_score=r.actual_conversion_score,
            actual_ctr=r.actual_ctr,
            context=r.context,
        )
        for r in rows
    ]


@router.post("/{experiment_id}/select-winner", response_model=WinnerResponse)
def select_winner(
    experiment_id: str,
    db: Session = Depends(get_db),
) -> WinnerResponse:
    """Select and mark the winning variant for an experiment."""
    winner = _svc.select_winner(db, experiment_id)
    if winner is None:
        raise HTTPException(
            status_code=404,
            detail=f"No variant records found for experiment '{experiment_id}'",
        )
    weight_profile = _svc.get_winner_weight_profile(db, experiment_id)
    return WinnerResponse(
        ok=True,
        experiment_id=experiment_id,
        winner_id=winner.id,
        winner_score=winner.actual_conversion_score or winner.winner_score,
        weight_profile=weight_profile,
    )


# Variant-level outcome endpoint lives under a separate prefix
outcome_router = APIRouter(prefix="/api/v1/commerce/variants", tags=["commerce"])


@outcome_router.get("/{variant_id}/outcome", response_model=OutcomeResponse)
def get_variant_outcome(
    variant_id: str,
    db: Session = Depends(get_db),
) -> OutcomeResponse:
    """Return the recorded conversion outcome for a specific variant."""
    from app.models.variant_run_record import VariantRunRecord

    row: VariantRunRecord | None = (
        db.query(VariantRunRecord)
        .filter(VariantRunRecord.context["variant_id"].as_string() == variant_id)
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Variant '{variant_id}' not found",
        )
    return OutcomeResponse(
        ok=True,
        variant_id=variant_id,
        actual_conversion_score=row.actual_conversion_score,
        actual_ctr=row.actual_ctr,
        outcome_recorded_at=(
            row.outcome_recorded_at.isoformat() if row.outcome_recorded_at else None
        ),
        context=row.context,
    )
