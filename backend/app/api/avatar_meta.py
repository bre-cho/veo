from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.autovis import AvatarRole, TemplateFamily
from app.repositories.localization_repo import LocalizationRepo
from app.schemas.avatar_meta import (
    MetaCountryRead,
    MetaMarketProfileRead,
    MetaRoleRead,
    MetaTemplateRead,
)

router = APIRouter(prefix="/api/v1/meta", tags=["meta"])

_loc_repo = LocalizationRepo()

_LANGUAGES = [
    {"code": "en", "name": "English", "rtl": False},
    {"code": "ar", "name": "Arabic", "rtl": True},
    {"code": "es", "name": "Spanish", "rtl": False},
    {"code": "fr", "name": "French", "rtl": False},
    {"code": "de", "name": "German", "rtl": False},
    {"code": "pt", "name": "Portuguese", "rtl": False},
    {"code": "zh", "name": "Chinese", "rtl": False},
    {"code": "hi", "name": "Hindi", "rtl": False},
    {"code": "ja", "name": "Japanese", "rtl": False},
    {"code": "ko", "name": "Korean", "rtl": False},
]

_VOICES = [
    {"id": "voice_en_female_1", "name": "Emma (EN)", "language_code": "en", "accent_code": "us", "gender": "female"},
    {"id": "voice_en_male_1", "name": "James (EN)", "language_code": "en", "accent_code": "us", "gender": "male"},
    {"id": "voice_es_female_1", "name": "Sofia (ES)", "language_code": "es", "accent_code": "latam", "gender": "female"},
    {"id": "voice_ar_male_1", "name": "Khalid (AR)", "language_code": "ar", "accent_code": "gulf", "gender": "male"},
]

_OUTFITS = [
    {"code": "business_casual", "name": "Business Casual", "category": "professional"},
    {"code": "formal", "name": "Formal", "category": "professional"},
    {"code": "streetwear", "name": "Streetwear", "category": "casual"},
    {"code": "athleisure", "name": "Athleisure", "category": "casual"},
    {"code": "traditional_abaya", "name": "Traditional Abaya", "category": "cultural"},
]

_BACKGROUNDS = [
    {"code": "studio_white", "name": "Studio White", "category": "studio"},
    {"code": "studio_dark", "name": "Studio Dark", "category": "studio"},
    {"code": "office", "name": "Office", "category": "environment"},
    {"code": "outdoor_city", "name": "Outdoor City", "category": "environment"},
    {"code": "abstract_gradient", "name": "Abstract Gradient", "category": "abstract"},
]


@router.get("/countries")
def get_countries(db: Session = Depends(get_db)):
    profiles = _loc_repo.list_profiles(db)
    return [
        MetaCountryRead(
            market_code=p.market_code,
            country_name=p.country_name,
            language_code=p.language_code,
            currency_code=p.currency_code,
        )
        for p in profiles
    ]


@router.get("/languages")
def get_languages():
    return _LANGUAGES


@router.get("/roles")
def get_roles(db: Session = Depends(get_db)):
    roles = db.query(AvatarRole).order_by(AvatarRole.name).all()
    return [
        MetaRoleRead(
            id=r.id,
            name=r.name,
            description=r.description,
            niche_tags=r.niche_tags,
        )
        for r in roles
    ]


@router.get("/voices")
def get_voices():
    return _VOICES


@router.get("/outfits")
def get_outfits():
    return _OUTFITS


@router.get("/backgrounds")
def get_backgrounds():
    return _BACKGROUNDS


@router.get("/templates")
def get_templates(db: Session = Depends(get_db)):
    families = db.query(TemplateFamily).filter(TemplateFamily.is_active.is_(True)).order_by(TemplateFamily.name).all()
    return [
        MetaTemplateRead(
            id=f.id,
            name=f.name,
            content_goal=f.content_goal,
            niche_tags=f.niche_tags,
            is_active=f.is_active,
        )
        for f in families
    ]


@router.get("/market-profiles")
def get_market_profiles(db: Session = Depends(get_db)):
    profiles = _loc_repo.list_profiles(db)
    return [
        MetaMarketProfileRead(
            market_code=p.market_code,
            country_name=p.country_name,
            language_code=p.language_code,
            currency_code=p.currency_code,
            rtl=p.rtl,
            preferred_niches=p.preferred_niches,
            preferred_roles=p.preferred_roles,
        )
        for p in profiles
    ]
