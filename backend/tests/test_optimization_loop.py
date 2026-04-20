from __future__ import annotations

from app.schemas.optimization import OptimizationInput
from app.services.optimization_engine import OptimizationEngine


def test_low_hook_metrics_generates_hook_rewrite() -> None:
    engine = OptimizationEngine()
    result = engine.analyze(OptimizationInput(metrics={"hook_strength": 0.2, "cta_quality": 0.8}))
    assert any(s.type == "hook" for s in result.rewrite_suggestions)


def test_weak_cta_metrics_generates_cta_rewrite() -> None:
    engine = OptimizationEngine()
    result = engine.analyze(OptimizationInput(metrics={"hook_strength": 0.8, "cta_quality": 0.2}))
    assert any(s.type == "cta" for s in result.rewrite_suggestions)


def test_optimization_output_has_rewrite_suggestions() -> None:
    engine = OptimizationEngine()
    result = engine.analyze(OptimizationInput(metrics={"hook_strength": 0.2, "cta_quality": 0.2, "clarity": 0.2}))
    assert result.rewrite_suggestions
