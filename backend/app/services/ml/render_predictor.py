"""NumPy-based render predictor for Phase 3 autopilot recommendations.

Provides:
- RenderPredictor: lightweight logistic-regression model (NumPy only, no
  scikit-learn runtime required for inference) that predicts:
    * fail_risk   – probability that a job will have ≥1 failed scene
    * slow_render – probability that render duration exceeds a threshold
- persist / load helpers to a JSON sidecar file
- ModelTrainer: trains the model from a labelled DataFrame
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.services.ml.feature_engineering import (
    JOB_FEATURE_COLS,
    apply_normalization,
    build_job_features,
    normalize_matrix,
    to_feature_matrix,
)

logger = logging.getLogger(__name__)

_SLOW_RENDER_SECONDS = 600.0  # 10 min threshold for "slow" classification


# ── Logistic regression (NumPy) ───────────────────────────────────────────────


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))


def _binary_cross_entropy(y: np.ndarray, p: np.ndarray) -> float:
    eps = 1e-12
    return float(-np.mean(y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps)))


def _train_logistic(
    X: np.ndarray,
    y: np.ndarray,
    *,
    lr: float = 0.05,
    epochs: int = 500,
    l2: float = 0.01,
) -> np.ndarray:
    """Gradient-descent logistic regression. Returns weight vector (n_features+1,)."""
    n, d = X.shape
    w = np.zeros(d + 1)
    X_b = np.hstack([np.ones((n, 1)), X])
    for _ in range(epochs):
        p = _sigmoid(X_b @ w)
        grad = X_b.T @ (p - y) / n
        grad[1:] += l2 * w[1:]
        w -= lr * grad
    return w


class RenderPredictor:
    """Dual-head predictor: fail_risk + slow_render.

    Attributes
    ----------
    weights_fail  : np.ndarray | None
    weights_slow  : np.ndarray | None
    norm_mean     : np.ndarray | None
    norm_std      : np.ndarray | None
    feature_cols  : list[str]
    is_trained    : bool
    """

    def __init__(self) -> None:
        self.weights_fail: np.ndarray | None = None
        self.weights_slow: np.ndarray | None = None
        self.norm_mean: np.ndarray | None = None
        self.norm_std: np.ndarray | None = None
        self.feature_cols: list[str] = JOB_FEATURE_COLS
        self.is_trained: bool = False

    # ── Training ──────────────────────────────────────────────────────────────

    def train(self, df: pd.DataFrame) -> dict[str, Any]:
        """Train both heads from a job-feature DataFrame.

        Returns a dict with training loss values.
        """
        df_feat = build_job_features(df)
        X_raw = to_feature_matrix(df_feat, self.feature_cols)
        if X_raw.shape[0] == 0:
            raise ValueError("No training samples after feature extraction.")

        X_norm, mean, std = normalize_matrix(X_raw)
        self.norm_mean = mean
        self.norm_std = std

        y_fail = (df_feat.get("fail_ratio", pd.Series(0, index=df_feat.index)).fillna(0) > 0).astype(float).values
        y_slow = (df_feat.get("duration_seconds", pd.Series(-1, index=df_feat.index)).fillna(-1) > _SLOW_RENDER_SECONDS).astype(float).values

        self.weights_fail = _train_logistic(X_norm, y_fail)
        self.weights_slow = _train_logistic(X_norm, y_slow)
        self.is_trained = True

        p_fail = _sigmoid(np.hstack([np.ones((len(X_norm), 1)), X_norm]) @ self.weights_fail)
        p_slow = _sigmoid(np.hstack([np.ones((len(X_norm), 1)), X_norm]) @ self.weights_slow)
        return {
            "samples": int(X_raw.shape[0]),
            "loss_fail": _binary_cross_entropy(y_fail, p_fail),
            "loss_slow": _binary_cross_entropy(y_slow, p_slow),
        }

    # ── Inference ─────────────────────────────────────────────────────────────

    def predict(self, features: dict[str, Any]) -> dict[str, float]:
        """Predict fail_risk and slow_render probability for a single job.

        Parameters
        ----------
        features : dict mapping feature name → numeric value.
        """
        if not self.is_trained or self.weights_fail is None or self.weights_slow is None:
            return {"fail_risk": 0.5, "slow_render": 0.5, "is_trained": False}

        row = {col: float(features.get(col, 0)) for col in self.feature_cols}
        X = np.array([[row[c] for c in self.feature_cols]], dtype=np.float64)
        assert self.norm_mean is not None and self.norm_std is not None
        X_norm = apply_normalization(X, self.norm_mean, self.norm_std)
        X_b = np.hstack([np.ones((1, 1)), X_norm])
        return {
            "fail_risk": float(_sigmoid(X_b @ self.weights_fail)[0]),
            "slow_render": float(_sigmoid(X_b @ self.weights_slow)[0]),
            "is_trained": True,
        }

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self, path: str | Path) -> None:
        """Persist model weights to a JSON sidecar file."""
        payload: dict[str, Any] = {
            "feature_cols": self.feature_cols,
            "is_trained": self.is_trained,
        }
        if self.is_trained:
            payload["weights_fail"] = self.weights_fail.tolist()  # type: ignore[union-attr]
            payload["weights_slow"] = self.weights_slow.tolist()  # type: ignore[union-attr]
            payload["norm_mean"] = self.norm_mean.tolist()  # type: ignore[union-attr]
            payload["norm_std"] = self.norm_std.tolist()  # type: ignore[union-attr]
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info("RenderPredictor saved to %s", path)

    def load(self, path: str | Path) -> bool:
        """Load model weights from JSON. Returns True on success."""
        p = Path(path)
        if not p.exists():
            return False
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            self.feature_cols = data.get("feature_cols", JOB_FEATURE_COLS)
            self.is_trained = data.get("is_trained", False)
            if self.is_trained:
                self.weights_fail = np.array(data["weights_fail"])
                self.weights_slow = np.array(data["weights_slow"])
                self.norm_mean = np.array(data["norm_mean"])
                self.norm_std = np.array(data["norm_std"])
            return True
        except Exception as exc:
            logger.warning("Failed to load RenderPredictor from %s: %s", path, exc)
            return False


# ── Singleton accessor ────────────────────────────────────────────────────────

_PREDICTOR: RenderPredictor | None = None


def get_predictor(model_path: str | None = None) -> RenderPredictor:
    """Return (and lazily load) the singleton RenderPredictor."""
    global _PREDICTOR
    if _PREDICTOR is None:
        _PREDICTOR = RenderPredictor()
        if model_path:
            _PREDICTOR.load(model_path)
    return _PREDICTOR


def reset_predictor() -> None:
    """Reset singleton (used in tests)."""
    global _PREDICTOR
    _PREDICTOR = None


# ── Training entrypoint ───────────────────────────────────────────────────────


def train_predictor_from_db(
    db: Any,
    *,
    lookback_days: int = 30,
    model_path: str | None = None,
    min_samples: int = 10,
) -> dict[str, Any]:
    """Train the RenderPredictor from DB data and optionally persist it."""
    from app.services.ml.feature_engineering import load_jobs_dataframe, train_inference_split

    df_raw = load_jobs_dataframe(db, lookback_days=lookback_days)
    if len(df_raw) < min_samples:
        return {
            "ok": False,
            "reason": f"Insufficient training data: {len(df_raw)} samples (min={min_samples})",
        }

    df_feat = build_job_features(df_raw)
    train_df, _ = train_inference_split(df_feat)
    if len(train_df) < min_samples:
        return {
            "ok": False,
            "reason": f"Insufficient training samples after split: {len(train_df)}",
        }

    predictor = get_predictor()
    metrics = predictor.train(train_df)
    if model_path:
        predictor.save(model_path)

    return {"ok": True, **metrics}
