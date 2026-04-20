import sys
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.channel_plan import ChannelPlan  # noqa: F401
from app.models.creative_engine_run import CreativeEngineRun  # noqa: F401
from app.models.optimization_run import OptimizationRun  # noqa: F401
from app.models.performance_record import PerformanceRecord  # noqa: F401
from app.models.publish_job import PublishJob  # noqa: F401


class _RedisFixtureClient:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str) -> bool:
        self._store[key] = value
        return True

    def delete(self, key: str) -> int:
        existed = key in self._store
        self._store.pop(key, None)
        return int(existed)

    def flushall(self) -> None:
        self._store.clear()


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Generator[Session, None, None]:
    local_session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False, expire_on_commit=False)
    session = local_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def redis_client() -> _RedisFixtureClient:
    return _RedisFixtureClient()


@pytest.fixture()
def auth_token() -> str:
    return "test-auth-token"


@pytest.fixture()
def seeded_data(db_session: Session) -> dict[str, str]:
    return {"seed": "ok", "session_bind": str(db_session.get_bind())}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        path = str(item.fspath).lower()
        if "smoke" in path or "happy_path" in path:
            item.add_marker(pytest.mark.smoke)
        elif "api" in path or "integration" in path:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
