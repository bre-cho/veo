import json
import time

from celery import Celery
from redis import Redis

from apps.api.core.config import settings
from apps.api.db.session import SessionLocal
from apps.api.models.core import BillingUsage, Brand, Job, JobStatus, PosterVariant, Project, ProjectStatus
from packages.prompt_engine.beauty import generate_variant_prompts
from packages.provider_adapters.adobe import AdobeMockAdapter, AdobeProductionAdapter
from packages.provider_adapters.base import ProviderError
from packages.provider_adapters.canva import CanvaMockAdapter, CanvaProductionAdapter
from packages.scoring_engine.rules import score_prompt

celery_app = Celery("poster_engine", broker=settings.redis_url, backend=settings.redis_url)


def _redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def _set_job_progress(job_id: str, progress: int, current_step: str) -> None:
    _redis().setex(
        f"job:{job_id}:progress",
        settings.idempotency_ttl_seconds,
        json.dumps({"progress": progress, "current_step": current_step}),
    )


def _retry_call(fn, *args, **kwargs):
    last_error = None
    for attempt in range(1, 4):
        try:
            return fn(*args, **kwargs)
        except ProviderError as exc:
            last_error = exc
            if not exc.retryable:
                raise
            if attempt < 3:
                time.sleep(2 ** (attempt - 1))
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(2 ** (attempt - 1))
    raise last_error


def _build_adobe_adapter():
    if settings.adobe_mode.lower() == "production":
        if not settings.adobe_api_key or not settings.adobe_client_id:
            raise ProviderError(
                "adobe",
                "AUTH",
                retryable=False,
                message="Missing ADOBE_API_KEY or ADOBE_CLIENT_ID",
            )
        return AdobeProductionAdapter(
            access_token=settings.adobe_api_key,
            client_id=settings.adobe_client_id,
        )
    return AdobeMockAdapter()


def _build_canva_adapter():
    if settings.canva_mode.lower() == "production":
        access_token = settings.canva_access_token
        if not access_token:
            raise ProviderError("canva", "AUTH", retryable=False, message="Missing CANVA_ACCESS_TOKEN")
        return CanvaProductionAdapter(access_token=access_token)
    return CanvaMockAdapter()

@celery_app.task
def ping():
    return "pong"


@celery_app.task
def generate_project_job(project_id: str, job_id: str) -> dict:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        project = db.get(Project, project_id)
        if not job or not project:
            return {"ok": False, "error": "job_or_project_not_found"}
        brand = db.get(Brand, project.brand_id)
        if not brand:
            job.status = JobStatus.failed
            job.error_message = "brand_not_found"
            db.add(job)
            db.commit()
            _set_job_progress(job_id, 100, "failed")
            return {"ok": False, "error": "brand_not_found"}

        job.status = JobStatus.running
        db.add(job)
        db.commit()
        _set_job_progress(job_id, 10, "generating_prompts")

        prompts = generate_variant_prompts(
            project={"product_name": project.product_name, "offer": project.offer},
            brand={"brand_voice": brand.brand_voice},
        )
        if len(prompts) > settings.api_budget_per_project:
            job.status = JobStatus.failed
            job.error_message = "budget_exceeded"
            db.add(job)
            db.commit()
            _set_job_progress(job_id, 100, "failed_budget_exceeded")
            return {"ok": False, "error": "budget_exceeded"}

        adobe = _build_adobe_adapter()
        canva = _build_canva_adapter()
        created_variant_ids: list[str] = []
        provider_audit = []

        total = max(len(prompts), 1)
        for index, item in enumerate(prompts, start=1):
            adobe_result = _retry_call(
                adobe.generate_visual,
                item["prompt"],
                {
                    "brand": brand.name,
                    "brand_voice": brand.brand_voice,
                    "colors": brand.colors,
                    "fonts": brand.fonts,
                    "campaign_type": project.campaign_type,
                },
            )
            canva_result = _retry_call(
                canva.create_layout,
                {
                    "prompt": item["prompt"],
                    "brand": brand.name,
                    "brand_id": brand.id,
                    "offer": project.offer,
                    "template_id": project.metadata_json.get("template_id"),
                },
            )
            scores = score_prompt(item["prompt"], item["variant_type"])

            provider_name = f"{adobe_result.get('provider')}+{canva_result.get('provider')}"

            variant = PosterVariant(
                project_id=project.id,
                variant_type=item["variant_type"],
                prompt=item["prompt"],
                provider=provider_name,
                adobe_asset_id=adobe_result.get("adobe_asset_id"),
                canva_design_id=canva_result.get("canva_design_id"),
                ctr_score=scores["ctr_score"],
                attention_score=scores["attention_score"],
                luxury_score=scores["luxury_score"],
                trust_score=scores["trust_score"],
                product_focus=scores["product_focus"],
                conversion_score=scores["conversion_score"],
                final_score=scores["final_score"],
                status=scores["status"],
            )
            db.add(variant)
            db.flush()
            db.add(
                BillingUsage(
                    owner_user_id=project.owner_user_id,
                    brand_id=brand.id,
                    project_id=project.id,
                    event_type="variant_generated",
                    units=1,
                    metadata_json={"variant_id": variant.id, "provider": provider_name},
                )
            )
            created_variant_ids.append(variant.id)
            provider_audit.append(
                {
                    "variant_type": item["variant_type"],
                    "adobe": adobe_result,
                    "canva": canva_result,
                }
            )

            progress = 10 + int((index / total) * 80)
            _set_job_progress(job_id, progress, f"generated_{index}_of_{total}")

        project.status = ProjectStatus.scored
        job.status = JobStatus.done
        job.output_json = {
            "created_variant_ids": created_variant_ids,
            "provider_audit": provider_audit,
            "variant_count": len(created_variant_ids),
        }
        db.add(project)
        db.add(job)
        db.commit()

        _set_job_progress(job_id, 100, "done")
        return {"ok": True, "created_variant_ids": created_variant_ids}
    except Exception as exc:
        job = db.get(Job, job_id)
        if job:
            job.status = JobStatus.failed
            job.error_message = str(exc)
            db.add(job)
            db.commit()
        _set_job_progress(job_id, 100, "failed")
        return {"ok": False, "error": str(exc)}
    finally:
        db.close()
