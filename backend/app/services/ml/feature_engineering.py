"""Feature engineering from render job/scene data using Pandas and NumPy.

This module provides:
- Ingestion of RenderJob + RenderSceneTask records into Pandas DataFrames.
- Feature extraction and normalisation with NumPy.
- Train / inference dataset split helpers.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models.render_job import RenderJob
from app.models.render_scene_task import RenderSceneTask

logger = logging.getLogger(__name__)

# ── Column definitions ──────────────────────────────────────────────────────

JOB_FEATURE_COLS = [
    "planned_scene_count",
    "provider_veo",
    "provider_runway",
    "provider_kling",
    "provider_other",
    "hour_of_day",
    "day_of_week",
]

SCENE_FEATURE_COLS = [
    "retry_count",
    "poll_fallback_enabled",
    "provider_veo",
    "provider_runway",
    "provider_kling",
    "provider_other",
    "scene_index_norm",
]

# ── DB → DataFrame ───────────────────────────────────────────────────────────


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def load_jobs_dataframe(
    db: Session,
    *,
    lookback_days: int = 30,
    statuses: list[str] | None = None,
) -> pd.DataFrame:
    """Return a DataFrame of completed RenderJob rows for the lookback window."""
    statuses = statuses or ["done", "failed", "cancelled"]
    cutoff = _utcnow() - timedelta(days=lookback_days)
    rows = (
        db.query(RenderJob)
        .filter(
            RenderJob.status.in_(statuses),
            RenderJob.created_at >= cutoff,
        )
        .all()
    )
    if not rows:
        return pd.DataFrame(columns=["id", "project_id", "provider", "status",
                                     "planned_scene_count", "completed_scene_count",
                                     "failed_scene_count", "created_at",
                                     "started_at", "completed_at"])
    records = [
        {
            "id": r.id,
            "project_id": r.project_id,
            "provider": r.provider,
            "status": r.status,
            "planned_scene_count": r.planned_scene_count or 0,
            "completed_scene_count": r.completed_scene_count or 0,
            "failed_scene_count": r.failed_scene_count or 0,
            "created_at": r.created_at,
            "started_at": r.started_at,
            "completed_at": r.completed_at,
        }
        for r in rows
    ]
    return pd.DataFrame(records)


def load_scenes_dataframe(
    db: Session,
    *,
    job_ids: list[str] | None = None,
    lookback_days: int = 30,
) -> pd.DataFrame:
    """Return a DataFrame of RenderSceneTask rows."""
    cutoff = _utcnow() - timedelta(days=lookback_days)
    q = db.query(RenderSceneTask).filter(RenderSceneTask.created_at >= cutoff)
    if job_ids:
        q = q.filter(RenderSceneTask.job_id.in_(job_ids))
    rows = q.all()
    if not rows:
        return pd.DataFrame(columns=["id", "job_id", "scene_index", "provider",
                                     "status", "retry_count", "poll_fallback_enabled",
                                     "created_at", "submitted_at", "finished_at",
                                     "failure_code", "failure_category"])
    records = [
        {
            "id": r.id,
            "job_id": r.job_id,
            "scene_index": r.scene_index,
            "provider": r.provider,
            "status": r.status,
            "retry_count": r.retry_count or 0,
            "poll_fallback_enabled": int(r.poll_fallback_enabled),
            "created_at": r.created_at,
            "submitted_at": r.submitted_at,
            "finished_at": r.finished_at,
            "failure_code": r.failure_code,
            "failure_category": r.failure_category,
        }
        for r in rows
    ]
    return pd.DataFrame(records)


# ── Feature engineering ──────────────────────────────────────────────────────


def _provider_dummies(df: pd.DataFrame, col: str = "provider") -> pd.DataFrame:
    """Add one-hot columns for known providers."""
    for prov in ("veo", "runway", "kling"):
        df[f"provider_{prov}"] = (df[col] == prov).astype(int)
    df["provider_other"] = (~df[col].isin(["veo", "runway", "kling"])).astype(int)
    return df


def build_job_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer features for job-level ML tasks."""
    df = df.copy()
    df = _provider_dummies(df)
    df["hour_of_day"] = pd.to_datetime(df["created_at"]).dt.hour.fillna(0).astype(int)
    df["day_of_week"] = pd.to_datetime(df["created_at"]).dt.dayofweek.fillna(0).astype(int)
    df["duration_seconds"] = (
        (pd.to_datetime(df["completed_at"]) - pd.to_datetime(df["started_at"]))
        .dt.total_seconds()
        .fillna(-1)
    )
    df["fail_ratio"] = df["failed_scene_count"] / df["planned_scene_count"].clip(lower=1)
    return df


def build_scene_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer features for scene-level ML tasks."""
    df = df.copy()
    df = _provider_dummies(df)
    max_idx = df["scene_index"].max() or 1
    df["scene_index_norm"] = df["scene_index"] / max(max_idx, 1)
    df["scene_duration_seconds"] = (
        (pd.to_datetime(df["finished_at"]) - pd.to_datetime(df["submitted_at"]))
        .dt.total_seconds()
        .fillna(-1)
    )
    return df


# ── NumPy normalisation ───────────────────────────────────────────────────────


def to_feature_matrix(
    df: pd.DataFrame,
    feature_cols: list[str],
) -> np.ndarray:
    """Extract and return a float64 feature matrix from the DataFrame."""
    available = [c for c in feature_cols if c in df.columns]
    matrix = df[available].fillna(0).astype(np.float64).values
    return matrix


def normalize_matrix(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Z-score normalise; return (X_norm, mean, std).

    Columns with zero std are left as-is (std treated as 1).
    """
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std_safe = np.where(std == 0, 1.0, std)
    return (X - mean) / std_safe, mean, std


def apply_normalization(
    X: np.ndarray,
    mean: np.ndarray,
    std: np.ndarray,
) -> np.ndarray:
    """Apply a pre-computed normalisation (mean/std) to a new matrix."""
    std_safe = np.where(std == 0, 1.0, std)
    return (X - mean) / std_safe


# ── Train / inference split ───────────────────────────────────────────────────


def train_inference_split(
    df: pd.DataFrame,
    *,
    train_ratio: float = 0.8,
    time_col: str = "created_at",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Chronological split: older rows → train, newer rows → inference."""
    df_sorted = df.sort_values(time_col, ascending=True).reset_index(drop=True)
    split_idx = int(len(df_sorted) * train_ratio)
    return df_sorted.iloc[:split_idx].copy(), df_sorted.iloc[split_idx:].copy()


# ── Summary stats ─────────────────────────────────────────────────────────────


def compute_job_summary_stats(df: pd.DataFrame) -> dict[str, Any]:
    """Return descriptive statistics dict for a job feature DataFrame."""
    if df.empty:
        return {}
    numeric = df.select_dtypes(include=[np.number])
    desc = numeric.describe().to_dict()
    return {col: {k: (float(v) if isinstance(v, (np.integer, np.floating)) else v)
                  for k, v in stats.items()}
            for col, stats in desc.items()}
