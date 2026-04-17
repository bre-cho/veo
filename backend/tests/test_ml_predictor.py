"""Tests for ml/render_predictor.py"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.render_job import RenderJob
from app.services.ml.render_predictor import (
    RenderPredictor,
    get_predictor,
    reset_predictor,
    train_predictor_from_db,
)


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _add_done_jobs(db, count: int = 20) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for i in range(count):
        db.add(RenderJob(
            id=f"job-pred-{i}",
            project_id=f"proj-{i}",
            provider="veo" if i % 2 == 0 else "runway",
            status="done" if i % 5 != 0 else "failed",
            planned_scene_count=max(1, i % 5 + 1),
            completed_scene_count=max(0, (i % 5)),
            failed_scene_count=1 if i % 5 == 0 else 0,
            created_at=now,
            started_at=now,
            completed_at=now,
        ))
    db.commit()


# ── RenderPredictor unit ──────────────────────────────────────────────────────


def test_predictor_untrained_returns_defaults():
    predictor = RenderPredictor()
    result = predictor.predict({"planned_scene_count": 3})
    assert result["fail_risk"] == 0.5
    assert result["slow_render"] == 0.5
    assert result["is_trained"] is False


def test_predictor_train_succeeds():
    import pandas as pd

    n = 30
    data = {
        "planned_scene_count": list(range(1, n + 1)),
        "provider": ["veo"] * 15 + ["runway"] * 15,
        "status": ["done"] * 25 + ["failed"] * 5,
        "completed_scene_count": list(range(1, n + 1)),
        "failed_scene_count": [0] * 25 + [1] * 5,
        "created_at": [datetime.now(timezone.utc).replace(tzinfo=None)] * n,
        "started_at": [datetime.now(timezone.utc).replace(tzinfo=None)] * n,
        "completed_at": [datetime.now(timezone.utc).replace(tzinfo=None)] * n,
    }
    df = pd.DataFrame(data)
    predictor = RenderPredictor()
    metrics = predictor.train(df)
    assert metrics["samples"] == n
    assert "loss_fail" in metrics
    assert "loss_slow" in metrics
    assert predictor.is_trained


def test_predictor_predict_returns_probabilities():
    import pandas as pd

    n = 25
    data = {
        "planned_scene_count": [3] * n,
        "provider": ["veo"] * n,
        "status": ["done"] * n,
        "completed_scene_count": [3] * n,
        "failed_scene_count": [0] * n,
        "created_at": [datetime.now(timezone.utc).replace(tzinfo=None)] * n,
        "started_at": [datetime.now(timezone.utc).replace(tzinfo=None)] * n,
        "completed_at": [datetime.now(timezone.utc).replace(tzinfo=None)] * n,
    }
    predictor = RenderPredictor()
    predictor.train(pd.DataFrame(data))
    result = predictor.predict({
        "planned_scene_count": 3,
        "provider_veo": 1,
        "provider_runway": 0,
        "provider_kling": 0,
        "provider_other": 0,
        "hour_of_day": 10,
        "day_of_week": 1,
    })
    assert 0.0 <= result["fail_risk"] <= 1.0
    assert 0.0 <= result["slow_render"] <= 1.0
    assert result["is_trained"] is True


def test_predictor_save_load_roundtrip(tmp_path):
    import pandas as pd

    n = 20
    data = {
        "planned_scene_count": list(range(1, n + 1)),
        "provider": ["veo"] * n,
        "status": ["done"] * n,
        "completed_scene_count": list(range(1, n + 1)),
        "failed_scene_count": [0] * n,
        "created_at": [datetime.now(timezone.utc).replace(tzinfo=None)] * n,
        "started_at": [datetime.now(timezone.utc).replace(tzinfo=None)] * n,
        "completed_at": [datetime.now(timezone.utc).replace(tzinfo=None)] * n,
    }
    p = RenderPredictor()
    p.train(pd.DataFrame(data))
    path = tmp_path / "model.json"
    p.save(str(path))

    p2 = RenderPredictor()
    ok = p2.load(str(path))
    assert ok
    assert p2.is_trained
    np.testing.assert_allclose(p.weights_fail, p2.weights_fail, atol=1e-6)


def test_predictor_load_missing_file(tmp_path):
    p = RenderPredictor()
    ok = p.load(str(tmp_path / "nonexistent.json"))
    assert ok is False
    assert p.is_trained is False


# ── DB-backed training ────────────────────────────────────────────────────────


def test_train_predictor_from_db_success():
    reset_predictor()
    db = _session()
    _add_done_jobs(db, count=20)
    result = train_predictor_from_db(db, lookback_days=30, min_samples=5)
    assert result["ok"] is True
    assert result["samples"] >= 5
    reset_predictor()


def test_train_predictor_from_db_insufficient_data():
    reset_predictor()
    db = _session()
    _add_done_jobs(db, count=3)
    result = train_predictor_from_db(db, lookback_days=30, min_samples=10)
    assert result["ok"] is False
    assert "Insufficient" in result["reason"]
    reset_predictor()


# ── Singleton ─────────────────────────────────────────────────────────────────


def test_get_predictor_returns_same_instance():
    reset_predictor()
    p1 = get_predictor()
    p2 = get_predictor()
    assert p1 is p2
    reset_predictor()
