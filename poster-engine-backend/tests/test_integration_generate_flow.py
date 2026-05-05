import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import apps.api.main as main_module
import apps.worker.celery_app as worker_module
from apps.api.core.config import settings
from apps.api.db.session import Base, get_db


class InMemoryRedis:
    def __init__(self):
        self.store: dict[str, str] = {}

    def get(self, key: str):
        return self.store.get(key)

    def setex(self, key: str, _ttl: int, value):
        if not isinstance(value, str):
            value = json.dumps(value) if isinstance(value, dict) else str(value)
        self.store[key] = value


def test_generate_to_export_flow_integration(monkeypatch, tmp_path: Path):
    settings.app_env = "local"
    settings.auth_jwt_secret = "integration-secret"
    settings.auth_jwt_algorithm = "HS256"
    settings.dev_internal_token_secret = "integration-dev-secret"
    settings.storage_provider = "local"
    settings.storage_dir = str(tmp_path / "storage")
    settings.adobe_mode = "mock"
    settings.canva_mode = "mock"

    db_path = tmp_path / "integration.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    fake_redis = InMemoryRedis()

    def immediate_delay(**kwargs):
        return worker_module.generate_project_job(**kwargs)

    monkeypatch.setattr(main_module, "_run_migrations", lambda: None)
    monkeypatch.setattr(main_module, "_redis", lambda: fake_redis)
    monkeypatch.setattr(worker_module, "_redis", lambda: fake_redis)
    monkeypatch.setattr(worker_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(main_module.generate_project_job, "delay", immediate_delay)

    main_module.app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(main_module.app) as client:
            token_res = client.post(
                "/internal/dev/token",
                json={"user_id": "user-it", "email": "it@example.com", "expires_in_seconds": 1800},
                headers={"x-dev-internal-secret": settings.dev_internal_token_secret},
            )
            assert token_res.status_code == 200
            access_token = token_res.json()["access_token"]
            auth_headers = {"Authorization": f"Bearer {access_token}"}

            brand_res = client.post(
                "/api/v1/brands",
                json={"name": "Integration Brand"},
                headers=auth_headers,
            )
            assert brand_res.status_code == 200
            brand_id = brand_res.json()["id"]

            project_res = client.post(
                "/api/v1/projects",
                json={"brand_id": brand_id, "product_name": "Integration Lipstick"},
                headers=auth_headers,
            )
            assert project_res.status_code == 200
            project_id = project_res.json()["id"]

            generate_res = client.post(
                f"/api/v1/projects/{project_id}/generate",
                headers={**auth_headers, "Idempotency-Key": "it-key-1"},
            )
            assert generate_res.status_code == 200
            job_id = generate_res.json()["job_id"]

            events_res = client.get(f"/api/v1/jobs/{job_id}/events", headers=auth_headers)
            assert events_res.status_code == 200
            events_data = events_res.json()
            assert events_data["status"] == "done"
            assert events_data["progress"] == 100
            assert events_data["variant_count"] >= 1

            variants_res = client.get(f"/api/v1/projects/{project_id}/variants", headers=auth_headers)
            assert variants_res.status_code == 200
            variants = variants_res.json()
            assert len(variants) >= 1

            variant_id = variants[0]["id"]
            export_res = client.post(f"/api/v1/variants/{variant_id}/export", headers=auth_headers)
            assert export_res.status_code == 200
            manifest = export_res.json()["manifest"]
            assert manifest["variant_id"] == variant_id
            assert len(manifest["assets"]) == 3
            assert all(asset["signed_url"].startswith("file://") for asset in manifest["assets"])
    finally:
        main_module.app.dependency_overrides.clear()
