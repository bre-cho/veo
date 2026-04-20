from __future__ import annotations

from fastapi import APIRouter

from app.schemas.product_ingestion import ProductIngestionRequest, NormalizedProductProfile
from app.services.commerce.product_ingestion_service import ProductIngestionService

router = APIRouter(prefix="/api/v1/commerce", tags=["commerce"])

_product_ingestion_service = ProductIngestionService()


@router.post("/ingest-product", response_model=NormalizedProductProfile)
def ingest_product(req: ProductIngestionRequest):
    return _product_ingestion_service.ingest(req)
