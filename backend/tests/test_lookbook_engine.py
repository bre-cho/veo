from __future__ import annotations

from app.schemas.lookbook import LookbookRequest
from app.services.lookbook_engine import LookbookEngine


def _products() -> list[dict]:
    return [
        {"name": "Jacket", "style": "street"},
        {"name": "Pants", "style": "street"},
        {"name": "Shoes", "style": "street"},
        {"name": "Bag", "style": "minimal"},
    ]


def test_products_to_outfit_sequences() -> None:
    engine = LookbookEngine()
    result = engine.generate(LookbookRequest(products=_products()))
    assert result.outfit_sequences


def test_scene_pack_not_empty() -> None:
    engine = LookbookEngine()
    result = engine.generate(LookbookRequest(products=_products()))
    assert result.scene_pack


def test_video_plan_valid() -> None:
    engine = LookbookEngine()
    result = engine.generate(LookbookRequest(products=_products()))
    assert result.video_plan["scene_count"] > 0
