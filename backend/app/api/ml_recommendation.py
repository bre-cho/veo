"""ML recommendation API endpoints.

Endpoints
---------
POST /api/v1/ml/train          – Train the RenderPredictor from DB data.
POST /api/v1/ml/predict        – Predict fail_risk + slow_render for a feature set.
GET  /api/v1/ml/feature-stats  – Describe features from recent job data.
GET  /api/v1/ml/status         – Model status (trained, feature cols).
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.ml_recommendation_log import MlRecommendationLog
from app.schemas.ml_recommendation import (
    FeatureSummaryResponse,
    PredictRequest,
    PredictResponse,
    TrainRequest,
    TrainResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ml", tags=["ml-recommendation"])


def _make_recommendation(fail_risk: float, slow_render: float) -> str | None:
    """Map prediction scores to a human-readable recommendation string."""
    parts = []
    if fail_risk >= 0.7:
        parts.append("High fail risk – consider pre-flight provider check or lower batch size.")
    elif fail_risk >= 0.4:
        parts.append("Moderate fail risk – monitor scene tasks closely.")
    if slow_render >= 0.7:
        parts.append("Likely slow render – allocate extra time or schedule in off-peak hours.")
    elif slow_render >= 0.4:
        parts.append("Moderate render time expected.")
    return " ".join(parts) if parts else None


@router.post("/train", response_model=TrainResponse)
async def train_model(payload: TrainRequest, db: Session = Depends(get_db)):
    """Train the RenderPredictor from recent job history."""
    if not settings.ml_enabled:
        raise HTTPException(status_code=503, detail="ML is disabled via ML_ENABLED=false")

    from app.services.ml.render_predictor import train_predictor_from_db

    result = train_predictor_from_db(
        db,
        lookback_days=payload.lookback_days,
        model_path=settings.ml_model_path,
        min_samples=payload.min_samples,
    )
    if not result.get("ok"):
        return TrainResponse(ok=False, reason=result.get("reason"))
    return TrainResponse(
        ok=True,
        samples=result.get("samples", 0),
        loss_fail=result.get("loss_fail"),
        loss_slow=result.get("loss_slow"),
    )


@router.post("/predict", response_model=PredictResponse)
async def predict(payload: PredictRequest, db: Session = Depends(get_db)):
    """Predict fail risk and render duration for a given feature vector."""
    if not settings.ml_enabled:
        raise HTTPException(status_code=503, detail="ML is disabled via ML_ENABLED=false")

    from app.services.ml.render_predictor import get_predictor

    predictor = get_predictor(model_path=settings.ml_model_path)
    scores = predictor.predict(payload.features)

    recommendation = _make_recommendation(scores["fail_risk"], scores["slow_render"])

    # Persist prediction to audit log.
    log_entry = MlRecommendationLog(
        id=str(uuid.uuid4()),
        job_id=payload.job_id,
        fail_risk=scores["fail_risk"],
        slow_render=scores["slow_render"],
        feature_snapshot=payload.features,
        recommendation=recommendation,
    )
    db.add(log_entry)
    db.commit()

    return PredictResponse(
        fail_risk=scores["fail_risk"],
        slow_render=scores["slow_render"],
        is_trained=scores.get("is_trained", False),
        recommendation=recommendation,
        job_id=payload.job_id,
    )


@router.get("/feature-stats", response_model=FeatureSummaryResponse)
async def feature_stats(
    lookback_days: int = 30,
    db: Session = Depends(get_db),
):
    """Return descriptive statistics over recent job features."""
    from app.services.ml.feature_engineering import (
        build_job_features,
        compute_job_summary_stats,
        load_jobs_dataframe,
    )

    df_raw = load_jobs_dataframe(db, lookback_days=lookback_days)
    if df_raw.empty:
        return FeatureSummaryResponse(stats={}, sample_count=0)
    df_feat = build_job_features(df_raw)
    return FeatureSummaryResponse(
        stats=compute_job_summary_stats(df_feat),
        sample_count=len(df_feat),
    )


@router.get("/status")
async def ml_status():
    """Return model readiness status."""
    from app.services.ml.render_predictor import get_predictor

    predictor = get_predictor(model_path=settings.ml_model_path)
    return {
        "ok": True,
        "ml_enabled": settings.ml_enabled,
        "is_trained": predictor.is_trained,
        "feature_cols": predictor.feature_cols,
        "model_path": settings.ml_model_path,
    }
