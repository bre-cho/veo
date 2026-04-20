from __future__ import annotations

from fastapi import APIRouter

from app.schemas.trend_image import TrendImageRequest, TrendImageResponse
from app.services.trend_image_engine import TrendImageEngine

router = APIRouter(prefix="/api/v1/trend-images", tags=["trend-images"])

_engine = TrendImageEngine()


@router.post("/generate", response_model=TrendImageResponse)
def generate_trend_images(req: TrendImageRequest) -> TrendImageResponse:
    return _engine.generate(req)
