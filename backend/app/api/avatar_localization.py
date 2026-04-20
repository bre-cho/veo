from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.avatar_localization import CountrySwitchRequest, CountrySwitchResponse
from app.services.localization.country_switch_service import CountrySwitchService

router = APIRouter(prefix="/api/v1", tags=["localization"])

_switch_service = CountrySwitchService()


@router.post("/system/switch-country", response_model=CountrySwitchResponse)
def switch_country(req: CountrySwitchRequest, db: Session = Depends(get_db)):
    result = _switch_service.switch_country(db, req.market_code)
    return CountrySwitchResponse(**result)
