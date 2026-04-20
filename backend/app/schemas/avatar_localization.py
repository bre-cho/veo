from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class CountrySwitchRequest(BaseModel):
    market_code: str
    user_id: Optional[str] = None


class CountrySwitchResponse(BaseModel):
    market_code: str
    country_name: str
    language_code: Optional[str] = None
    currency_code: Optional[str] = None
    rtl: bool = False
    status: str = "switched"


class LocalizationProfileRead(BaseModel):
    id: str
    market_code: str
    country_name: str
    language_code: Optional[str] = None
    currency_code: Optional[str] = None
    timezone: Optional[str] = None
    rtl: bool
    preferred_niches: Optional[Any] = None
    preferred_roles: Optional[Any] = None

    model_config = {"from_attributes": True}
