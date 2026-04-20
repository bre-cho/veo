from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_product_ingestion_route_still_available() -> None:
    response = client.post(
        "/api/v1/commerce/ingest-product",
        json={
            "product_name": "TaskFlow",
            "product_features": ["fast setup"],
            "target_audience": "teams",
        },
    )
    assert response.status_code == 200
    assert response.json().get("product_name") == "TaskFlow"
