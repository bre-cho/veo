from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

from kombu import Connection
from redis import Redis
from sqlalchemy import text

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import engine


def check_postgres() -> dict[str, Any]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True, "service": "postgres"}
    except Exception:
        return {"ok": False, "service": "postgres", "error": "Postgres connectivity check failed"}


def check_redis() -> dict[str, Any]:
    try:
        redis_client = Redis.from_url(settings.celery_broker_url)
        pong = redis_client.ping()
        return {"ok": bool(pong), "service": "redis"}
    except Exception as exc:
        return {"ok": False, "service": "redis", "error": str(exc)}

def check_object_storage() -> dict[str, Any]:
    if not settings.s3_endpoint_url:
        return {
            "ok": False,
            "service": "object_storage",
            "error": "Missing S3 endpoint configuration",
        }

    try:
        import httpx

        with httpx.Client(timeout=3.0, follow_redirects=True) as client:
            response = client.get(f"{settings.s3_endpoint_url.rstrip('/')}/minio/health/live")

        return {
            "ok": response.status_code == 200,
            "service": "object_storage",
            "status_code": response.status_code,
        }
    except Exception as exc:
        return {
            "ok": False,
            "service": "object_storage",
            "error": str(exc),
        }


def check_worker_config() -> dict[str, Any]:
    """
    Health check cơ bản cho Celery runtime.
    Hiện tại chỉ xác nhận broker/backend config có mặt.
    Có thể nâng cấp sau thành inspect ping worker thật.
    """
    missing = []

    if not settings.celery_broker_url:
        missing.append("CELERY_BROKER_URL")
    if not settings.celery_result_backend:
        missing.append("CELERY_RESULT_BACKEND")

    if missing:
        return {
            "ok": False,
            "service": "worker_config",
            "error": f"Missing worker config: {', '.join(missing)}",
        }

    return {
        "ok": True,
        "service": "worker_config",
        "broker_url": settings.celery_broker_url,
        "result_backend": settings.celery_result_backend,
    }


DEFAULT_EXPECTED_CELERY_QUEUES = (
    "celery",
    "render_dispatch",
    "render_poll",
    "render_postprocess",
    "render_callback",
    "render_maintenance",
    "audio",
    "template",
    "autopilot",
    "drama",
)


def _expected_worker_queues() -> list[str]:
    raw = os.getenv("CELERY_EXPECTED_QUEUES", "")
    if raw.strip():
        return sorted({item.strip() for item in raw.split(",") if item.strip()})
    return list(DEFAULT_EXPECTED_CELERY_QUEUES)


def _queue_names_from_active_queues(active_queues: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for worker_name, queues in (active_queues or {}).items():
        names: list[str] = []
        for queue in queues or []:
            name = queue.get("name") if isinstance(queue, dict) else None
            if name:
                names.append(str(name))
        result[worker_name] = sorted(set(names))
    return result


def _sum_task_counts(payload: dict[str, Any] | None) -> dict[str, int]:
    payload = payload or {}
    return {worker_name: len(items or []) for worker_name, items in payload.items()}


def check_celery_workers(timeout: float = 2.0, expected_queues: Iterable[str] | None = None) -> dict[str, Any]:
    expected = sorted(set(expected_queues or _expected_worker_queues()))

    try:
        inspect = celery_app.control.inspect(timeout=timeout)
        ping = inspect.ping() or {}
        stats = inspect.stats() or {}
        active_queues_raw = inspect.active_queues() or {}
        active = inspect.active() or {}
        reserved = inspect.reserved() or {}
        scheduled = inspect.scheduled() or {}

        worker_names = sorted(ping.keys())
        queue_map = _queue_names_from_active_queues(active_queues_raw)
        covered_queues = sorted({queue for queues in queue_map.values() for queue in queues})
        missing_queues = sorted(set(expected) - set(covered_queues))

        ok = bool(worker_names) and not missing_queues

        return {
            "ok": ok,
            "service": "celery_workers",
            "worker_count": len(worker_names),
            "workers": worker_names,
            "expected_queues": expected,
            "covered_queues": covered_queues,
            "missing_queues": missing_queues,
            "queues_by_worker": queue_map,
            "task_counts": {
                "active": _sum_task_counts(active),
                "reserved": _sum_task_counts(reserved),
                "scheduled": _sum_task_counts(scheduled),
            },
            "stats_available_for": sorted(stats.keys()),
            "timeout_seconds": timeout,
        }
    except Exception as exc:
        return {
            "ok": False,
            "service": "celery_workers",
            "error": str(exc),
            "expected_queues": expected,
            "timeout_seconds": timeout,
        }


def check_worker_runtime(timeout: float = 2.0) -> dict[str, Any]:
    config = check_worker_config()
    broker = check_celery_broker()

    if not config.get("ok") or not broker.get("ok"):
        return {
            "ok": False,
            "service": "worker_runtime",
            "config": config,
            "broker": broker,
            "workers": {
                "ok": False,
                "service": "celery_workers",
                "error": "Skipped worker inspect because config or broker is unhealthy",
            },
        }

    workers = check_celery_workers(timeout=timeout)
    return {
        "ok": bool(config.get("ok")) and bool(broker.get("ok")) and bool(workers.get("ok")),
        "service": "worker_runtime",
        "config": config,
        "broker": broker,
        "workers": workers,
    }


def summarize_health(checks: list[dict[str, Any]]) -> dict[str, Any]:
    ok = all(bool(check.get("ok")) for check in checks)

    return {
        "ok": ok,
        "service": "render_factory_api",
        "env": settings.app_env,
        "checks": checks,
    }


def check_celery_broker() -> dict[str, Any]:
    try:
        with Connection(settings.celery_broker_url) as conn:
            conn.ensure_connection(max_retries=1)
        return {"ok": True, "service": "celery_broker"}
    except Exception as exc:
        return {"ok": False, "service": "celery_broker", "error": str(exc)}


def build_full_health_payload() -> dict[str, Any]:
    postgres = check_postgres()
    redis = check_redis()
    object_storage = check_object_storage()
    runtime = check_worker_runtime()

    checks = {
        "postgres": postgres,
        "redis": redis,
        "object_storage": object_storage,
        "worker_runtime": runtime,
    }

    overall_ok = all(item.get("ok") for item in checks.values())

    return {
        "ok": overall_ok,
        "checks": checks,
    }
