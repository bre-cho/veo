from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.services.healthcheck_service import (
    check_object_storage,
    check_postgres,
    check_redis,
    check_worker_runtime,
    summarize_health,
)
from app.services.render_fsm import describe_fsm, get_transition_metrics_snapshot

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict:
    """
    Lightweight health endpoint — chỉ kiểm api + db + redis.
    Dùng cho docker compose depends_on healthcheck.
    """
    checks = [check_postgres(), check_redis()]
    return summarize_health(checks)


@router.get("/healthz/postgres")
async def healthz_postgres() -> dict:
    """
    Health check riêng cho Postgres.
    """
    return check_postgres()


@router.get("/healthz/redis")
async def healthz_redis() -> dict:
    """
    Health check riêng cho Redis/Celery broker.
    """
    return check_redis()


@router.get("/healthz/object-storage")
async def healthz_object_storage() -> dict:
    """
    Health check riêng cho MinIO/S3-compatible object storage.
    """
    return check_object_storage()


@router.get("/healthz/workers")
async def healthz_workers(response: Response) -> dict:
    """
    Runtime health check cho Celery — broker reachable + workers sống + queues covered.
    Trả về HTTP 503 nếu worker không healthy.
    """
    payload = check_worker_runtime(timeout=2.0)
    if not payload.get("ok"):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return payload


@router.get("/healthz/full")
async def healthz_full(response: Response) -> dict:
    """
    Full health check — api + db + redis + object storage + workers.
    Trả về HTTP 503 nếu bất kỳ dependency nào fail.
    """
    checks = [
        check_postgres(),
        check_redis(),
        check_object_storage(),
        check_worker_runtime(timeout=2.0),
    ]
    payload = summarize_health(checks)
    if not payload.get("ok"):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return payload


@router.get("/healthz/fsm")
async def healthz_fsm() -> dict:
    """
    Expose FSM metrics + transition map để debug orchestration.
    """
    return {
        "ok": True,
        "metrics": get_transition_metrics_snapshot(),
        "fsm": describe_fsm(),
    }
