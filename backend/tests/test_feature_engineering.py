"""Tests for ml/feature_engineering.py"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.render_job import RenderJob
from app.models.render_scene_task import RenderSceneTask
from app.services.ml.feature_engineering import (
    JOB_FEATURE_COLS,
    SCENE_FEATURE_COLS,
    apply_normalization,
    build_job_features,
    build_scene_features,
    compute_job_summary_stats,
    load_jobs_dataframe,
    load_scenes_dataframe,
    normalize_matrix,
    to_feature_matrix,
    train_inference_split,
)


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _add_jobs(db, count: int = 5, status: str = "done") -> list[str]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    ids = []
    for i in range(count):
        j = RenderJob(
            id=f"job-fe-{i}",
            project_id=f"proj-{i}",
            provider="veo",
            status=status,
            planned_scene_count=3,
            completed_scene_count=3 if status == "done" else 0,
            failed_scene_count=0,
            created_at=now,
            started_at=now,
            completed_at=now,
        )
        db.add(j)
        ids.append(j.id)
    db.commit()
    return ids


# ── DataFrame loading ─────────────────────────────────────────────────────────


def test_load_jobs_dataframe_returns_rows():
    db = _session()
    _add_jobs(db, count=3, status="done")
    df = load_jobs_dataframe(db, lookback_days=30)
    assert len(df) == 3
    assert "provider" in df.columns


def test_load_jobs_dataframe_empty_when_no_data():
    db = _session()
    df = load_jobs_dataframe(db, lookback_days=30)
    assert df.empty


def test_load_scenes_dataframe():
    db = _session()
    job_ids = _add_jobs(db, count=2, status="done")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for jid in job_ids:
        db.add(RenderSceneTask(
            id=f"scene-{jid}-0",
            job_id=jid,
            scene_index=0,
            title="S0",
            provider="veo",
            status="done",
            retry_count=1,
            poll_fallback_enabled=True,
            request_payload_json="{}",
            created_at=now,
        ))
    db.commit()
    df = load_scenes_dataframe(db, lookback_days=30)
    assert len(df) == 2


# ── Feature engineering ───────────────────────────────────────────────────────


def test_build_job_features_adds_expected_columns():
    db = _session()
    _add_jobs(db, count=4, status="done")
    df = load_jobs_dataframe(db, lookback_days=30)
    df_feat = build_job_features(df)
    for col in ("provider_veo", "hour_of_day", "day_of_week", "fail_ratio"):
        assert col in df_feat.columns


def test_build_scene_features_adds_provider_dummies():
    db = _session()
    job_ids = _add_jobs(db, count=2, status="done")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for jid in job_ids:
        db.add(RenderSceneTask(
            id=f"sc-{jid}",
            job_id=jid,
            scene_index=0,
            title="S",
            provider="runway",
            status="done",
            retry_count=0,
            poll_fallback_enabled=False,
            request_payload_json="{}",
            created_at=now,
        ))
    db.commit()
    df = load_scenes_dataframe(db, lookback_days=30)
    df_feat = build_scene_features(df)
    assert "provider_runway" in df_feat.columns
    assert df_feat["provider_runway"].sum() == 2


# ── NumPy helpers ─────────────────────────────────────────────────────────────


def test_to_feature_matrix_shape():
    df = pd.DataFrame({
        "planned_scene_count": [1, 2, 3],
        "provider_veo": [1, 1, 0],
        "provider_runway": [0, 0, 1],
        "provider_kling": [0, 0, 0],
        "provider_other": [0, 0, 0],
        "hour_of_day": [8, 12, 18],
        "day_of_week": [0, 2, 4],
    })
    X = to_feature_matrix(df, JOB_FEATURE_COLS)
    assert X.shape == (3, len(JOB_FEATURE_COLS))
    assert X.dtype == np.float64


def test_normalize_matrix_zero_mean():
    X = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    X_norm, mean, std = normalize_matrix(X)
    assert X_norm.shape == X.shape
    np.testing.assert_allclose(X_norm.mean(axis=0), [0.0, 0.0], atol=1e-6)


def test_normalize_constant_column():
    X = np.array([[5.0], [5.0], [5.0]])
    X_norm, mean, std = normalize_matrix(X)
    np.testing.assert_allclose(X_norm, [[0.0], [0.0], [0.0]], atol=1e-6)


def test_apply_normalization_consistent():
    X = np.random.rand(10, 3)
    X_norm, mean, std = normalize_matrix(X)
    X2 = np.random.rand(5, 3)
    X2_norm = apply_normalization(X2, mean, std)
    assert X2_norm.shape == X2.shape


# ── Train/inference split ─────────────────────────────────────────────────────


def test_train_inference_split_proportions():
    db = _session()
    _add_jobs(db, count=10, status="done")
    df = load_jobs_dataframe(db, lookback_days=30)
    train, infer = train_inference_split(df, train_ratio=0.8)
    assert len(train) + len(infer) == len(df)
    assert len(train) >= 8


# ── Summary stats ─────────────────────────────────────────────────────────────


def test_compute_job_summary_stats_empty():
    stats = compute_job_summary_stats(pd.DataFrame())
    assert stats == {}


def test_compute_job_summary_stats_returns_dict():
    db = _session()
    _add_jobs(db, count=3, status="done")
    df = load_jobs_dataframe(db, lookback_days=30)
    df_feat = build_job_features(df)
    stats = compute_job_summary_stats(df_feat)
    assert isinstance(stats, dict)
    assert "planned_scene_count" in stats
