from __future__ import annotations

from fastapi import APIRouter

from app.schemas.lookbook import LookbookRequest, LookbookResponse
from app.services.lookbook_engine import LookbookEngine

router = APIRouter(prefix="/api/v1/lookbook", tags=["lookbook"])

_engine = LookbookEngine()


@router.post("/generate", response_model=LookbookResponse)
def generate_lookbook(req: LookbookRequest) -> LookbookResponse:
    return _engine.generate(req)
