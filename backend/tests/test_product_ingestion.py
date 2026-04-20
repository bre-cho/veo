from __future__ import annotations

from app.schemas.product_ingestion import ProductIngestionRequest
from app.services.commerce.product_ingestion_service import ProductIngestionService


svc = ProductIngestionService()


def test_normalize_direct_payload() -> None:
    result = svc.ingest(
        ProductIngestionRequest(
            product_name="TaskFlow",
            product_features=["fast setup"],
            target_audience="teams",
        )
    )
    assert result.product_name == "TaskFlow"
    assert result.product_features


def test_customer_reviews_generate_social_proof() -> None:
    result = svc.ingest(
        ProductIngestionRequest(
            product_name="TaskFlow",
            customer_reviews=["Loved it", "Amazing results"],
        )
    )
    assert result.social_proof


def test_features_map_to_benefits_and_pain_points() -> None:
    result = svc.ingest(
        ProductIngestionRequest(
            product_name="TaskFlow",
            product_features=["solves slow onboarding"],
            product_description="hard and confusing setup before",
        )
    )
    assert result.benefits
    assert result.pain_points
