from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class MetaRoleRead(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    niche_tags: Optional[Any] = None


class MetaLanguageRead(BaseModel):
    code: str
    name: str
    rtl: bool = False


class MetaCountryRead(BaseModel):
    market_code: str
    country_name: str
    language_code: Optional[str] = None
    currency_code: Optional[str] = None


class MetaVoiceRead(BaseModel):
    id: str
    name: str
    language_code: Optional[str] = None
    accent_code: Optional[str] = None
    gender: Optional[str] = None


class MetaOutfitRead(BaseModel):
    code: str
    name: str
    category: Optional[str] = None
    preview_url: Optional[str] = None


class MetaBackgroundRead(BaseModel):
    code: str
    name: str
    category: Optional[str] = None
    preview_url: Optional[str] = None


class MetaTemplateRead(BaseModel):
    id: str
    name: str
    content_goal: Optional[str] = None
    niche_tags: Optional[Any] = None
    is_active: bool = True


class MetaMarketProfileRead(BaseModel):
    market_code: str
    country_name: str
    language_code: Optional[str] = None
    currency_code: Optional[str] = None
    rtl: bool = False
    preferred_niches: Optional[Any] = None
    preferred_roles: Optional[Any] = None
