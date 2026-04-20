from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.avatar_commerce import (
    CommerceCTARequest,
    CommerceCTAResponse,
    CommerceRecommendAvatarRequest,
    CommerceRecommendAvatarResponse,
    CommerceRecommendTemplateRequest,
    CommerceRecommendTemplateResponse,
    ContentGoalClassifyRequest,
    ContentGoalClassifyResponse,
    ProductTemplateRouterRequest,
    ProductTemplateRouterResponse,
)
from app.services.commerce.avatar_recommendation_service import AvatarRecommendationService
from app.services.commerce.content_goal_classifier import ContentGoalClassifier
from app.services.commerce.cta_recommendation_service import CTARecommendationService
from app.services.commerce.product_to_template_router import ProductToTemplateRouter
from app.services.commerce.template_recommendation_service import TemplateRecommendationService

router = APIRouter(prefix="/api/v1/commerce", tags=["commerce"])

_avatar_rec = AvatarRecommendationService()
_template_rec = TemplateRecommendationService()
_cta_rec = CTARecommendationService()
_classifier = ContentGoalClassifier()
_product_router = ProductToTemplateRouter()


@router.post("/recommend-avatar", response_model=CommerceRecommendAvatarResponse)
def recommend_avatar(req: CommerceRecommendAvatarRequest, db: Session = Depends(get_db)):
    avatars = _avatar_rec.recommend(
        db,
        content_goal=req.content_goal,
        niche_code=req.niche_code,
        market_code=req.market_code,
        limit=req.limit,
    )
    return CommerceRecommendAvatarResponse(
        content_goal=req.content_goal,
        avatars=[
            {"id": a.id, "name": a.name, "niche_code": a.niche_code, "market_code": a.market_code}
            for a in avatars
        ],
    )


@router.post("/recommend-template", response_model=CommerceRecommendTemplateResponse)
def recommend_template(req: CommerceRecommendTemplateRequest, db: Session = Depends(get_db)):
    templates = _template_rec.recommend(db, req.avatar_id, req.content_goal, req.limit)
    return CommerceRecommendTemplateResponse(
        avatar_id=req.avatar_id,
        content_goal=req.content_goal,
        templates=templates,
    )


@router.post("/recommend-cta", response_model=CommerceCTAResponse)
def recommend_cta(req: CommerceCTARequest):
    cta = _cta_rec.recommend(req.content_goal, req.conversion_mode)
    return CommerceCTAResponse(cta_text=cta, content_goal=req.content_goal)


@router.post("/classify-content-goal", response_model=ContentGoalClassifyResponse)
def classify_content_goal(req: ContentGoalClassifyRequest):
    goal, confidence = _classifier.classify_with_confidence(req.brief)
    return ContentGoalClassifyResponse(content_goal=goal, confidence=confidence)


@router.post("/router/product-template", response_model=ProductTemplateRouterResponse)
def route_product_template(req: ProductTemplateRouterRequest, db: Session = Depends(get_db)):
    result = _product_router.route(db, req.product_brief, req.market_code)
    return ProductTemplateRouterResponse(**result)
