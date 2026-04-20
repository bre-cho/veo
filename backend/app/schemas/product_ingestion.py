from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProductIngestionRequest(BaseModel):
    product_url: str | None = None
    product_name: str | None = None
    product_features: list[str] | None = None
    product_description: str | None = None
    customer_reviews: list[str] | None = None
    target_audience: str | None = None
    market_code: str | None = None
    source_type: str | None = None


class NormalizedProductProfile(BaseModel):
    product_name: str
    product_features: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    social_proof: list[str] = Field(default_factory=list)
    target_audience: str | None = None
    recommended_angles: list[str] = Field(default_factory=list)
    market_code: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
