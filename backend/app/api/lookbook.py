from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.lookbook import LookbookRequest, LookbookResponse
from app.services.lookbook_engine import LookbookEngine

router = APIRouter(prefix="/api/v1/lookbook", tags=["lookbook"])

_engine = LookbookEngine()


@router.post("/generate", response_model=LookbookResponse)
def generate_lookbook(req: LookbookRequest, db: Session = Depends(get_db)) -> LookbookResponse:
    return _engine.generate(req, db=db)
