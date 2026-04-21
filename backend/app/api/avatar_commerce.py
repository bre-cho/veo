from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.avatar_commerce import (
    CommerceCTARequest,
    CommerceCTAResponse,
    CommerceOptimizeRequest,
    CommerceOptimizeResponse,
    CommerceRecommendAvatarRequest,
    CommerceRecommendAvatarResponse,
    CommerceRecommendTemplateRequest,
    CommerceRecommendTemplateResponse,
    ContentGoalClassifyRequest,
    ContentGoalClassifyResponse,
    GrowthOptimizeRequest,
    ProductTemplateRouterRequest,
    ProductTemplateRouterResponse,
)
from app.schemas.review_video import (
    ConversionScoreResult,
    GenerateReviewVideoRequest,
    GenerateReviewVideoResponse,
    ReviewVideoSceneOut,
)
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
from app.services.channel_engine import ChannelEngine
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
_channel_engine = ChannelEngine()
_learning_engine = PerformanceLearningEngine()


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


@router.post("/generate-review-variants")
def generate_review_variants(payload: dict, db: Session = Depends(get_db)):
    from app.services.commerce.review_variant_engine import ReviewVariantEngine
    engine = ReviewVariantEngine()
    result = engine.generate_variants_with_history(
        product_profile=payload,
        count=payload.get("count", 5),
        platform=payload.get("platform"),
        db=db,
    )
    return {
        "variants": result["variants"],
        "winner": result["winner"],
        "run_id": result.get("run_id"),
    }


@router.get("/variant-history")
def variant_history(
    product_name: str | None = None,
    platform: str | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    from app.services.commerce.review_variant_engine import ReviewVariantEngine
    records = ReviewVariantEngine.get_history(
        product_name=product_name,
        platform=platform,
        limit=limit,
        db=db,
    )
    return {"records": records, "count": len(records)}


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
        persona_id=req.persona_id,
        product_category=req.product_category,
        funnel_stage=req.funnel_stage,
        campaign_id=req.campaign_id,
    )
    return {"ok": True, "video_id": record["video_id"]}


@router.get("/learning/summary", response_model=FeedbackSummaryResponse)
def learning_summary():
    return FeedbackSummaryResponse(**_learning_engine.feedback_summary())


@router.get("/learning/health", response_model=dict)
def learning_health():
    """Return data quality, drift diagnostics, and persona score matrix for the learning engine."""
    quality = _learning_engine.data_quality_report()
    drift = _learning_engine.score_drift_summary()
    persona_matrix = _learning_engine.persona_score_matrix()
    return {
        "data_quality": quality,
        "score_drift": drift,
        "persona_score_matrix": persona_matrix,
    }


@router.post("/optimize", response_model=CommerceOptimizeResponse)
def optimize_channel_plan(req: CommerceOptimizeRequest):
    """Generate an optimised channel plan respecting an optional budget constraint.

    Accepts the same fields as a standard channel plan request plus:

    - ``budget_constraint``: maximum total spend (in cost-per-post units).  When
      provided, the returned series plan is capped to
      ``floor(budget_constraint / cost_per_post)`` items.
    - ``objectives``: optional multi-objective weight dict forwarded to
      ``MultiObjectiveScorer`` for blended candidate scoring.
    """
    from app.schemas.channel import ChannelPlanRequest

    plan_req = ChannelPlanRequest(
        channel_name=req.channel_name,
        niche=req.niche,
        market_code=req.market_code,
        goal=req.goal,
        days=req.days,
        posts_per_day=req.posts_per_day,
        formats=req.formats,
        project_id=req.project_id,
        avatar_id=req.avatar_id,
        product_id=req.product_id,
        platform=req.platform,
    )

    result = _channel_engine.generate_plan(
        plan_req,
        learning_store=_learning_engine,
        budget_constraint=req.budget_constraint,
        objectives=req.objectives,
    )
    return CommerceOptimizeResponse(
        plan_id=result.plan_id,
        series_plan=[item.model_dump() for item in result.series_plan],
        publish_queue_count=result.publish_queue_count,
        calendar_summary=result.calendar_summary,
        candidates=[c.model_dump() for c in result.candidates],
        winner_candidate_id=result.winner_candidate_id,
    )


@router.get("/campaigns/{campaign_id}/attribution", response_model=dict)
def campaign_attribution(campaign_id: str, window_days: int = 7, n_touch: int = 3):
    """Return multi-touch attribution for a campaign's most recent conversion."""
    from app.services.commerce.campaign_attribution_service import CampaignAttributionService
    svc = CampaignAttributionService(learning_store=_learning_engine)
    conversion_event: dict = {"timestamp": None, "value": 1.0}
    result = svc.attribute_conversion(
        conversion_event=conversion_event,
        campaign_id=campaign_id,
        window_days=window_days,
        n_touch=n_touch,
    )
    funnel = svc.campaign_funnel_report(campaign_id)
    return {"attribution": result, "funnel": funnel}


@router.get("/campaigns/{campaign_id}/bid-hint", response_model=dict)
def campaign_bid_hint(campaign_id: str):
    """Return a bid optimisation hint for a campaign based on performance data."""
    from app.services.commerce.campaign_attribution_service import CampaignAttributionService
    svc = CampaignAttributionService(learning_store=_learning_engine)
    funnel = svc.campaign_funnel_report(campaign_id)
    # Compute a simple bid hint: if conversion_rate is high, suggest increasing bid
    conversion_rate = funnel.get("conversion_rate", 0.0)
    ctr = funnel.get("ctr", 0.0)
    if conversion_rate >= 0.1:
        hint = "increase_bid"
        rationale = f"Conversion rate {conversion_rate:.2%} is above 10% threshold."
    elif ctr < 0.01:
        hint = "improve_creative"
        rationale = f"CTR {ctr:.2%} is below 1%; improve hook/creative before raising bid."
    else:
        hint = "maintain_bid"
        rationale = "Performance is within normal range."
    return {
        "campaign_id": campaign_id,
        "bid_hint": hint,
        "rationale": rationale,
        "funnel_summary": funnel,
    }


@router.post("/calibration/apply", response_model=dict)
def apply_calibration(
    platform: str | None = None,
    product_category: str | None = None,
    db: Session = Depends(get_db),
):
    """Trigger a manual calibration sweep for a platform/category combination.

    Reads VariantRunRecord history, computes optimal dimension weights via
    linear regression, persists them to ScoringCalibration, and returns
    the new weight profile.
    """
    from app.services.commerce.scoring_calibration_applier import ScoringCalibrationApplier

    applier = ScoringCalibrationApplier(db=db)
    result = applier.run_calibration_sweep(
        platform=platform,
        product_category=product_category,
    )
    return result


@router.post("/growth/optimize", response_model=dict)
def growth_optimize(req: GrowthOptimizeRequest, db: Session = Depends(get_db)):
    """Joint budget + creative + conversion optimizer for a campaign.

    Combines ``MultiObjectiveScorer`` (with calibration), ``CampaignBudgetPolicy``
    feasibility filter, and creative feedback boosts to return a ranked allocation
    plan across variant candidates.

    Returns:
        - ``campaign_id``
        - ``ranked_candidates``: scored and sorted candidate list
        - ``budget_summary``: remaining / limit / feasible_count
        - ``top_pick``: highest-scoring budget-feasible candidate
        - ``allocation_plan``: per-candidate budget share and recommended publish count
        - ``objectives_used``: effective objective weights (after calibration)
    """
    from app.services.commerce.growth_optimization_orchestrator import GrowthOptimizationOrchestrator

    orchestrator = GrowthOptimizationOrchestrator(db=db, learning_store=_learning_engine)
    return orchestrator.optimize(
        campaign_id=req.campaign_id,
        candidates=req.candidates,
        objectives=req.objectives,
        budget_constraint=req.budget_constraint,
        platform=req.platform,
        product_category=req.product_category,
        market_code=req.market_code,
        goal=req.goal,
    )


@router.post("/attribution/{campaign_id}/record", response_model=dict)
def record_attribution_as_performance(
    campaign_id: str,
    conversion_value: float = 1.0,
    window_days: int = 7,
    n_touch: int = 3,
    db: Session = Depends(get_db),
):
    """Attribute a conversion and feed the result back into PerformanceLearningEngine.

    Each attributed touchpoint becomes a performance record tagged with
    ``campaign_id``, which feeds ``_derive_contextual_weight_adjustments()``
    in ChannelEngine automatically.
    """
    from app.services.commerce.campaign_attribution_service import CampaignAttributionService
    import time

    svc = CampaignAttributionService(learning_store=_learning_engine)
    conversion_event: dict = {"timestamp": time.time(), "value": conversion_value}
    attribution = svc.attribute_conversion(
        conversion_event=conversion_event,
        campaign_id=campaign_id,
        window_days=window_days,
        n_touch=n_touch,
    )

    engine = PerformanceLearningEngine(db=db)
    records_written = 0
    for touch in attribution.get("attributions", []):
        try:
            engine.record(
                video_id=str(touch.get("video_id") or f"{campaign_id}_attr_{records_written}"),
                hook_pattern=str(touch.get("hook_pattern") or "unknown"),
                cta_pattern="attribution_touch",
                template_family="attribution",
                conversion_score=float(touch.get("credit", 0.5)),
                campaign_id=campaign_id,
            )
            records_written += 1
        except Exception:
            pass

    return {
        "campaign_id": campaign_id,
        "attribution": attribution,
        "performance_records_written": records_written,
    }


@router.get("/intelligence/status", response_model=dict)
def intelligence_status(db: Session = Depends(get_db)):
    """Return the operational status of all data-driven intelligence layers.

    Surfaces data sufficiency, active detector type, calibration staleness,
    and per-layer confidence.  Useful for ops dashboards and self-monitoring.
    """
    from datetime import datetime, timedelta, timezone

    from app.models.performance_record import PerformanceRecord
    from app.models.scoring_calibration import ScoringCalibration
    from app.models.objection_patterns import ObjectionPattern
    from app.models.variant_run_record import VariantRunRecord

    record_count = 0
    try:
        record_count = db.query(PerformanceRecord).count()
    except Exception:
        pass

    variant_count = 0
    try:
        variant_count = db.query(VariantRunRecord).count()
    except Exception:
        pass

    objection_count = 0
    try:
        objection_count = db.query(ObjectionPattern).filter(ObjectionPattern.is_active.is_(True)).count()
    except Exception:
        pass

    # Scoring calibration staleness
    calibration_status: dict = {"available": False}
    try:
        latest_cal = (
            db.query(ScoringCalibration)
            .order_by(ScoringCalibration.calibrated_at.desc())
            .first()
        )
        if latest_cal is not None:
            age_days = (
                datetime.now(timezone.utc).replace(tzinfo=None) - latest_cal.calibrated_at
            ).days
            calibration_status = {
                "available": True,
                "platform": latest_cal.platform,
                "product_category": latest_cal.product_category,
                "sample_count": latest_cal.sample_count,
                "r_squared": latest_cal.r_squared,
                "age_days": age_days,
                "stale": age_days > 7,
            }
    except Exception:
        pass

    return {
        "layers": {
            "category_detection": {
                "active_detector": "statistical" if record_count >= 50 else "keyword",
                "record_count": record_count,
                "sufficient_for_statistical": record_count >= 50,
                "confidence": "high" if record_count >= 50 else "low",
            },
            "persona_inference": {
                "active_detector": "data_driven" if record_count >= 10 else "keyword",
                "record_count": record_count,
                "sufficient_for_data_driven": record_count >= 10,
                "confidence": "medium" if record_count >= 10 else "low",
            },
            "conversion_scoring": {
                "calibration": calibration_status,
                "sufficient_for_calibration": variant_count >= 30,
                "variant_count": variant_count,
            },
            "objection_extraction": {
                "pattern_count": objection_count,
                "active_detector": "db" if objection_count > 0 else "hardcoded",
                "confidence": "high" if objection_count >= 10 else "low",
            },
        },
        "overall_health": "healthy" if record_count >= 50 and calibration_status.get("available") and not calibration_status.get("stale") else "degraded",
    }

