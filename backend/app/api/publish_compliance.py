"""Publish compliance API endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.publish_providers.compliance_risk_policy import (
    PLATFORM_RULES,
    ComplianceRiskPolicy,
)

router = APIRouter(prefix="/api/v1/publish/compliance", tags=["publish"])


class ComplianceEvaluateRequest(BaseModel):
    platform: str
    tier: str = "standard"
    title: str = ""
    description: str = ""
    caption: str = ""
    tags: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    duration_seconds: float | None = None
    adult_content: bool = False


class ComplianceEvaluateResponse(BaseModel):
    compliance_status: str
    risk_score: float
    risk_flags: list[str]
    platform: str
    tier: str


class PlatformRulesResponse(BaseModel):
    platform: str
    max_duration_seconds: int | None = None
    restricted_keywords: list[str]
    prohibited_categories: list[str]


@router.get("/rules/{platform}", response_model=PlatformRulesResponse)
def get_compliance_rules(platform: str) -> PlatformRulesResponse:
    """Return the compliance rules for a platform."""
    rules = PLATFORM_RULES.get(platform.lower())
    if rules is None:
        raise HTTPException(
            status_code=404,
            detail=f"No compliance rules found for platform '{platform}'",
        )
    return PlatformRulesResponse(
        platform=platform,
        max_duration_seconds=rules.get("max_duration_seconds"),
        restricted_keywords=rules.get("restricted_keywords", []),
        prohibited_categories=rules.get("prohibited_categories", []),
    )


@router.post("/evaluate", response_model=ComplianceEvaluateResponse)
def evaluate_compliance(
    body: ComplianceEvaluateRequest,
    db: Session = Depends(get_db),
) -> ComplianceEvaluateResponse:
    """Evaluate content against platform compliance rules."""
    policy = ComplianceRiskPolicy()
    content: dict[str, Any] = {
        "title": body.title,
        "description": body.description,
        "caption": body.caption,
        "tags": body.tags,
        "categories": body.categories,
        "adult_content": body.adult_content,
    }
    if body.duration_seconds is not None:
        content["duration_seconds"] = body.duration_seconds

    # Load custom thresholds if configured
    try:
        from app.models.risk_threshold_config import RiskThresholdConfig
        config = (
            db.query(RiskThresholdConfig)
            .filter(
                RiskThresholdConfig.platform == body.platform.lower(),
                RiskThresholdConfig.customer_tier == body.tier,
            )
            .first()
        )
        # Future: pass config to policy for custom thresholds
    except Exception:
        pass

    result = policy.evaluate(content, platform=body.platform, tier=body.tier)
    return ComplianceEvaluateResponse(
        compliance_status=result.compliance_status,
        risk_score=result.risk_score,
        risk_flags=result.risk_flags,
        platform=result.platform,
        tier=result.tier,
    )
