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
from app.schemas.review_video import (
    ConversionScoreResult,
    GenerateReviewVideoRequest,
    GenerateReviewVideoResponse,
    ReviewVideoSceneOut,
)
from app.schemas.product_ingestion import ProductIngestionRequest, NormalizedProductProfile
from app.schemas.storyboard import (
    AnalyticsActionItem,
    AnalyticsActionRequest,
    AnalyticsActionResponse,
    ComboRecommendRequest,
    ComboRecommendResponse,
    FeedbackSummaryResponse,
    GenerateCTARequest,
    GenerateCTAResponse,
    GenerateComparisonVideoRequest,
    GenerateHookRequest,
    GenerateHookResponse,
    GenerateTestimonialVideoRequest,
    RecordPerformanceRequest,
    TemplateIntelligenceRequest,
    TemplateIntelligenceResponse,
)
from app.services.analytics_action_service import AnalyticsActionService
from app.services.commerce.avatar_recommendation_service import AvatarRecommendationService
from app.services.commerce.combo_recommender import AvatarTemplateComboRecommender
from app.services.commerce.content_goal_classifier import ContentGoalClassifier
from app.services.commerce.cta_engine import CTAEngine
from app.services.commerce.cta_recommendation_service import CTARecommendationService
from app.services.commerce.extended_review_engine import (
    ComparisonVideoEngine,
    TestimonialVideoEngine,
)
from app.services.commerce.hook_engine import HookEngine
from app.services.commerce.product_to_template_router import ProductToTemplateRouter
from app.services.commerce.review_engine import ConversionScoreService, ReviewVideoEngine
from app.services.commerce.product_ingestion_service import ProductIngestionService
from app.services.commerce.template_recommendation_service import TemplateRecommendationService
from app.services.learning_engine import PerformanceLearningEngine
from app.services.template_intelligence import TemplateIntelligenceService

router = APIRouter(prefix="/api/v1/commerce", tags=["commerce"])

_avatar_rec = AvatarRecommendationService()
_template_rec = TemplateRecommendationService()
_cta_rec = CTARecommendationService()
_classifier = ContentGoalClassifier()
_product_router = ProductToTemplateRouter()
_review_engine = ReviewVideoEngine()
_conversion_score_svc = ConversionScoreService()
_hook_engine = HookEngine()
_cta_engine = CTAEngine()
_testimonial_engine = TestimonialVideoEngine()
_comparison_engine = ComparisonVideoEngine()
_template_intel_svc = TemplateIntelligenceService()
_combo_recommender = AvatarTemplateComboRecommender()
_analytics_action_svc = AnalyticsActionService()
_learning_engine = PerformanceLearningEngine()
_product_ingestion_service = ProductIngestionService()


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


@router.post("/generate-review-video", response_model=GenerateReviewVideoResponse)
def generate_review_video(req: GenerateReviewVideoRequest):
    script = _review_engine.generate(
        product_name=req.product_name,
        product_features=req.product_features,
        target_audience=req.target_audience,
        conversion_mode=req.conversion_mode,
        market_code=req.market_code,
        avatar_id=req.avatar_id,
    )
    score_result = _conversion_score_svc.score_script(script)
    preview_payload = script.to_preview_payload(
        aspect_ratio=req.aspect_ratio,
        target_platform=req.target_platform,
        avatar_id=req.avatar_id,
        market_code=req.market_code,
    )
    return GenerateReviewVideoResponse(
        product_name=script.product_name,
        target_audience=script.target_audience,
        content_goal=script.content_goal,
        conversion_mode=script.conversion_mode,
        hook=script.hook,
        body=script.body,
        cta=script.cta,
        scenes=[ReviewVideoSceneOut(**s.to_dict()) for s in script.scenes],
        conversion_score_result=ConversionScoreResult(**score_result),
        preview_payload=preview_payload,
    )


@router.post("/ingest-product", response_model=NormalizedProductProfile)
def ingest_product(req: ProductIngestionRequest):
    return _product_ingestion_service.ingest(req)


@router.post("/generate-review-variants")
def generate_review_variants(payload: dict):
    result = _review_engine.generate_review_variants(product_payload=payload, variant_count=payload.get("count", 5))
    return {
        "variants": result["variants"],
        "winner": result["winner"],
        "normalized_product_profile": result["normalized_product_profile"],
    }


@router.post("/select-review-winner")
def select_review_winner(payload: dict):
    variants = payload.get("variants") or []
    winner = _review_engine.select_review_winner(variants)
    return {"winner": winner}


@router.post("/generate-cta", response_model=GenerateCTAResponse)
def generate_cta(req: GenerateCTARequest):
    if req.all_variants:
        variants = _cta_engine.generate_all(
            intent=req.intent,
            product_name=req.product_name,
            target_audience=req.target_audience,
            discount=req.discount,
            deadline=req.deadline,
        )
        cta_text = variants[0] if variants else ""
    else:
        cta_text = _cta_engine.generate(
            intent=req.intent,
            product_name=req.product_name,
            target_audience=req.target_audience,
            discount=req.discount,
            deadline=req.deadline,
        )
        variants = []
    return GenerateCTAResponse(intent=req.intent, cta_text=cta_text, variants=variants)


@router.post("/generate-hook", response_model=GenerateHookResponse)
def generate_hook(req: GenerateHookRequest):
    if req.all_variants:
        variants = _hook_engine.generate_all(
            template_type=req.template_type,
            product_name=req.product_name,
            pain_hint=req.pain_hint,
            target_audience=req.target_audience,
            stat=req.stat,
        )
        hook_text = variants[0] if variants else ""
    else:
        hook_text = _hook_engine.generate(
            template_type=req.template_type,
            product_name=req.product_name,
            pain_hint=req.pain_hint,
            target_audience=req.target_audience,
            stat=req.stat,
        )
        variants = []
    return GenerateHookResponse(
        template_type=req.template_type, hook_text=hook_text, variants=variants
    )


@router.post("/generate-testimonial-video", response_model=GenerateReviewVideoResponse)
def generate_testimonial_video(req: GenerateTestimonialVideoRequest):
    script = _testimonial_engine.generate(
        product_name=req.product_name,
        product_features=req.product_features,
        target_audience=req.target_audience,
        conversion_mode=req.conversion_mode,
        market_code=req.market_code,
        avatar_id=req.avatar_id,
        hook_variant=req.hook_variant,
    )
    score_result = _conversion_score_svc.score_script(script)
    preview_payload = script.to_preview_payload(
        aspect_ratio=req.aspect_ratio,
        target_platform=req.target_platform,
        avatar_id=req.avatar_id,
        market_code=req.market_code,
    )
    return GenerateReviewVideoResponse(
        product_name=script.product_name,
        target_audience=script.target_audience,
        content_goal=script.content_goal,
        conversion_mode=script.conversion_mode,
        hook=script.hook,
        body=script.body,
        cta=script.cta,
        scenes=[ReviewVideoSceneOut(**s.to_dict()) for s in script.scenes],
        conversion_score_result=ConversionScoreResult(**score_result),
        preview_payload=preview_payload,
    )


@router.post("/generate-comparison-video", response_model=GenerateReviewVideoResponse)
def generate_comparison_video(req: GenerateComparisonVideoRequest):
    script = _comparison_engine.generate(
        product_name=req.product_name,
        competitor_name=req.competitor_name,
        product_features=req.product_features,
        target_audience=req.target_audience,
        conversion_mode=req.conversion_mode,
        market_code=req.market_code,
        avatar_id=req.avatar_id,
        hook_variant=req.hook_variant,
    )
    score_result = _conversion_score_svc.score_script(script)
    preview_payload = script.to_preview_payload(
        aspect_ratio=req.aspect_ratio,
        target_platform=req.target_platform,
        avatar_id=req.avatar_id,
        market_code=req.market_code,
    )
    return GenerateReviewVideoResponse(
        product_name=script.product_name,
        target_audience=script.target_audience,
        content_goal=script.content_goal,
        conversion_mode=script.conversion_mode,
        hook=script.hook,
        body=script.body,
        cta=script.cta,
        scenes=[ReviewVideoSceneOut(**s.to_dict()) for s in script.scenes],
        conversion_score_result=ConversionScoreResult(**score_result),
        preview_payload=preview_payload,
    )


@router.post("/template-intelligence", response_model=TemplateIntelligenceResponse)
def get_template_intelligence(req: TemplateIntelligenceRequest):
    result = _template_intel_svc.resolve(req.content_goal, req.market_code)
    return TemplateIntelligenceResponse(**result)


@router.post("/recommend-combo", response_model=ComboRecommendResponse)
def recommend_combo(req: ComboRecommendRequest):
    combo = _combo_recommender.recommend(
        content_goal=req.content_goal,
        market_code=req.market_code,
        conversion_mode=req.conversion_mode,
        candidate_avatars=req.candidate_avatars or [],
    )
    return ComboRecommendResponse(**combo.to_dict())


@router.post("/analytics-action", response_model=AnalyticsActionResponse)
def analytics_action(req: AnalyticsActionRequest):
    actions = _analytics_action_svc.suggest(
        conversion_score=req.conversion_score,
        details=req.details,
        content_goal=req.content_goal,
        market_code=req.market_code,
        current_template_family=req.current_template_family,
    )
    return AnalyticsActionResponse(
        suggestion_count=len(actions),
        actions=[AnalyticsActionItem(**a) for a in actions],
    )


@router.post("/learning/record", response_model=dict)
def record_performance(req: RecordPerformanceRequest):
    record = _learning_engine.record(
        video_id=req.video_id,
        hook_pattern=req.hook_pattern,
        cta_pattern=req.cta_pattern,
        template_family=req.template_family,
        conversion_score=req.conversion_score,
        view_count=req.view_count,
        click_through_rate=req.click_through_rate,
    )
    return {"ok": True, "video_id": record["video_id"]}


@router.get("/learning/summary", response_model=FeedbackSummaryResponse)
def learning_summary():
    return FeedbackSummaryResponse(**_learning_engine.feedback_summary())
