from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.schemas.optimization import OptimizationInput, OptimizationResponse
from app.services.optimization_engine import OptimizationEngine

router = APIRouter(prefix="/api/v1/optimization", tags=["optimization"])

_engine = OptimizationEngine()


class RewritePreviewRequest(BaseModel):
    preview_payload: dict
    optimization_response: OptimizationResponse | dict


@router.post("/analyze", response_model=OptimizationResponse)
def analyze_optimization(payload: OptimizationInput) -> OptimizationResponse:
    return _engine.analyze(payload)


@router.post("/rewrite-preview")
def rewrite_preview(req: RewritePreviewRequest):
    updated = _engine.rewrite_preview_payload(req.preview_payload, req.optimization_response)
    return {"preview_payload": updated}
