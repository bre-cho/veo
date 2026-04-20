from __future__ import annotations

from app.schemas.trend_image import TrendImageRequest
from app.services.trend_image_engine import TrendImageEngine


engine = TrendImageEngine()


def test_generate_concept_list() -> None:
    result = engine.generate(TrendImageRequest(topic="keto snacks"))
    assert result.concepts


def test_each_concept_has_prompt_and_trend_score() -> None:
    result = engine.generate(TrendImageRequest(topic="keto snacks", count=3))
    assert all(c.prompt_text for c in result.concepts)
    assert all(c.trend_score >= 0 for c in result.concepts)


def test_select_winner() -> None:
    result = engine.generate(TrendImageRequest(topic="keto snacks", count=3))
    assert result.recommended_winner_id
