# 03 — Backend Code Guide

Các block dưới đây là code skeleton để dev copy vào repo rồi chỉnh theo model field thực tế.

---

## 1. `backend/app/factory/factory_artifact_validator.py`

```python
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ArtifactValidationResult:
    ok: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class FactoryArtifactValidator:
    """Validate real render/audio/subtitle/manifest artifacts.

    Rule:
    - production: missing render artifact = issue/block
    - dev/test: missing render artifact can be warning only if explicitly async
    """

    def __init__(self, app_env: str | None = None) -> None:
        self.app_env = (app_env or os.getenv("APP_ENV") or "development").lower()

    def validate(
        self,
        *,
        render_job: Any | None,
        render_manifest: dict[str, Any] | str | None,
        scenes: list[dict[str, Any]],
        audio_url: str | None,
        output_video_url: str | None,
        allow_async_render: bool = False,
    ) -> ArtifactValidationResult:
        issues: list[str] = []
        warnings: list[str] = []
        details: dict[str, Any] = {}

        # 1. RenderJob presence
        if render_job is None:
            issues.append("render_job_missing")

        # 2. Output artifact URL/path
        final_url = output_video_url
        if render_job is not None:
            final_url = final_url or getattr(render_job, "final_video_url", None) or getattr(render_job, "output_url", None)
            details["render_status"] = getattr(render_job, "status", None)
            details["storage_key"] = getattr(render_job, "storage_key", None)

        details["output_video_url"] = final_url
        if not final_url:
            if allow_async_render and self.app_env != "production":
                warnings.append("render_output_pending_async")
            else:
                issues.append("render_output_missing")

        # 3. Local file readability when URL is local path
        if final_url and not str(final_url).startswith(("http://", "https://", "s3://", "gs://")):
            path = Path(str(final_url))
            if not path.exists():
                issues.append("render_file_not_found")
            elif path.stat().st_size <= 0:
                issues.append("render_file_empty")

        # 4. Manifest parse
        manifest: dict[str, Any] | None = None
        if render_manifest:
            try:
                manifest = json.loads(render_manifest) if isinstance(render_manifest, str) else render_manifest
            except Exception as exc:  # noqa: BLE001
                issues.append(f"manifest_parse_failed:{type(exc).__name__}")
        else:
            issues.append("manifest_missing")

        if manifest:
            manifest_scenes = manifest.get("scenes") or []
            details["manifest_scene_count"] = len(manifest_scenes)
            if not manifest_scenes:
                issues.append("manifest_has_no_scenes")
            if scenes and len(manifest_scenes) != len(scenes):
                issues.append("manifest_scene_count_mismatch")

            duration = manifest.get("estimated_duration_seconds")
            details["estimated_duration_seconds"] = duration
            if not duration or float(duration) <= 0:
                issues.append("invalid_manifest_duration")

            subtitle_segments = manifest.get("subtitle_segments") or []
            details["subtitle_segment_count"] = len(subtitle_segments)
            if scenes and not subtitle_segments:
                warnings.append("subtitle_segments_missing")

        # 5. Audio policy
        details["audio_url"] = audio_url
        if not audio_url:
            warnings.append("audio_url_missing")

        return ArtifactValidationResult(
            ok=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            details=details,
        )
```

---

## 2. `backend/app/factory/factory_render_completion.py`

```python
from __future__ import annotations

import os
import time
from typing import Any

from sqlalchemy.orm import Session


class FactoryRenderCompletionWatcher:
    """Poll RenderJob until completed/failed/timeout.

    Use short timeout in CI and dev. In production this can be async:
    - wait only when FACTORY_RENDER_WAIT_FOR_COMPLETION=1
    - otherwise QA should mark output as pending, not pass final QA.
    """

    TERMINAL_SUCCESS = {"succeeded", "completed", "success"}
    TERMINAL_FAILED = {"failed", "error", "cancelled", "blocked"}

    def __init__(self, db: Session, timeout_seconds: int | None = None, poll_interval: float = 1.0) -> None:
        self.db = db
        self.timeout_seconds = timeout_seconds or int(os.getenv("FACTORY_RENDER_WAIT_TIMEOUT_SECONDS", "60"))
        self.poll_interval = poll_interval

    def wait(self, render_job_id: str) -> dict[str, Any]:
        from app.models.render_job import RenderJob

        deadline = time.monotonic() + self.timeout_seconds
        last_status = None
        while time.monotonic() < deadline:
            job = self.db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
            if job is None:
                return {"completed": False, "failed": True, "status": "missing", "job": None}

            last_status = getattr(job, "status", None)
            if last_status in self.TERMINAL_SUCCESS:
                return {"completed": True, "failed": False, "status": last_status, "job": job}
            if last_status in self.TERMINAL_FAILED:
                return {"completed": False, "failed": True, "status": last_status, "job": job}

            self.db.expire_all()
            time.sleep(self.poll_interval)

        job = self.db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
        return {"completed": False, "failed": False, "timeout": True, "status": last_status, "job": job}
```

---

## 3. Patch `_stage_execute_render()` trong `factory_orchestrator.py`

Thay đoạn cuối của stage bằng logic này.

```python
        wait_for_completion = os.getenv("FACTORY_RENDER_WAIT_FOR_COMPLETION", "0") == "1"
        allow_async = not wait_for_completion

        completion = {"completed": False, "status": "queued"}
        render_job = None
        if wait_for_completion and ctx.project_id:
            from app.factory.factory_render_completion import FactoryRenderCompletionWatcher

            completion = FactoryRenderCompletionWatcher(self.db).wait(render_job_id)
            render_job = completion.get("job")

            if render_job and (getattr(render_job, "final_video_url", None) or getattr(render_job, "output_url", None)):
                ctx.output_video_url = getattr(render_job, "final_video_url", None) or getattr(render_job, "output_url", None)

        from app.factory.factory_artifact_validator import FactoryArtifactValidator

        artifact_result = FactoryArtifactValidator().validate(
            render_job=render_job,
            render_manifest=manifest,
            scenes=ctx.scenes,
            audio_url=ctx.audio_url,
            output_video_url=ctx.output_video_url,
            allow_async_render=allow_async,
        )
        ctx.extras["render_artifact_validation"] = artifact_result.__dict__

        # Production hard lock: if waiting for completion, artifact must be valid.
        if wait_for_completion and not artifact_result.ok:
            raise RuntimeError(f"render_artifact_invalid:{artifact_result.issues}")

        return {
            "render_job_id": render_job_id,
            "status": completion.get("status") or ("dispatched" if dispatched else "queued"),
            "dispatched": dispatched,
            "waited_for_completion": wait_for_completion,
            "completed": completion.get("completed", False),
            "manifest_scene_count": manifest.get("scene_count", 0),
            "estimated_duration_seconds": manifest.get("estimated_duration_seconds", 0),
            "artifact_validation": artifact_result.__dict__,
        }
```

Nhớ thêm import trong function:

```python
import os
```

---

## 4. Patch `FactoryQAVerifier.verify()`

Thêm tham số:

```python
artifact_validation: dict[str, Any] | None = None,
```

Thêm check:

```python
        artifact = artifact_validation or {}
        details["artifact_validation"] = artifact
        if artifact and artifact.get("ok") is False:
            for issue in artifact.get("issues", []):
                issues.append(f"artifact:{issue}")
            for warning in artifact.get("warnings", []):
                warnings.append(f"artifact:{warning}")
```

Trong `_stage_qa_validate()` truyền thêm:

```python
artifact_validation=ctx.extras.get("render_artifact_validation"),
```

---

## 5. `backend/app/factory/factory_publish_control.py`

```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session


class FactoryPublishControl:
    """Approval gate for live publishing."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def approve(self, run_id: str, approved_by: str | None = None) -> dict[str, Any]:
        from app.models.factory_run import FactoryRun

        run = self.db.query(FactoryRun).filter(FactoryRun.id == run_id).first()
        if run is None:
            raise ValueError("factory_run_not_found")

        metadata = getattr(run, "metadata_json", None) or getattr(run, "extra_json", None) or {}
        if isinstance(metadata, str):
            import json
            metadata = json.loads(metadata)

        metadata["publish_approved"] = True
        metadata["publish_approved_by"] = approved_by or "system"
        metadata["publish_approved_at"] = datetime.now(timezone.utc).isoformat()

        if hasattr(run, "metadata_json"):
            run.metadata_json = metadata
        elif hasattr(run, "extra_json"):
            run.extra_json = metadata

        self.db.commit()
        return metadata

    def is_approved(self, run: Any) -> bool:
        metadata = getattr(run, "metadata_json", None) or getattr(run, "extra_json", None) or {}
        if isinstance(metadata, str):
            import json
            metadata = json.loads(metadata)
        return bool(metadata.get("publish_approved"))
```

---

## 6. Patch `_stage_publish()`

```python
        dry_run = os.environ.get("FACTORY_PUBLISH_DRY_RUN", "1") != "0"
        live_requested = os.environ.get("FACTORY_LIVE_PUBLISH", "0") == "1"

        approved = False
        if live_requested:
            try:
                from app.models.factory_run import FactoryRun
                from app.factory.factory_publish_control import FactoryPublishControl

                run = self.db.query(FactoryRun).filter(FactoryRun.id == ctx.run_id).first()
                approved = FactoryPublishControl(self.db).is_approved(run) if run else False
            except Exception:
                approved = False

        if dry_run or not live_requested:
            ctx.publish_result = {"status": "dry_run", "requires_approval": True, **payload}
        elif live_requested and not approved:
            ctx.publish_result = {"status": "blocked_pending_approval", "requires_approval": True, **payload}
        else:
            # TODO: call YouTube/provider publish adapter here
            ctx.publish_result = {"status": "approved_publish_ready", "requires_approval": False, **payload}
```

---

## 7. `backend/app/factory/factory_retry_policy.py`

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryDecision:
    action: str  # retry | downgrade | human_review | block
    max_retries: int
    reason: str


class FactoryRetryPolicy:
    def decide(self, error_code: str | None, stage_name: str, attempt: int) -> RetryDecision:
        code = (error_code or "unknown_error").lower()

        if any(x in code for x in ["timeout", "connection", "temporary", "rate_limit"]):
            return RetryDecision("retry", 2, "transient_error")

        if any(x in code for x in ["db", "redis", "celery", "storage", "infra"]):
            return RetryDecision("retry", 1, "infra_error")

        if any(x in code for x in ["qa", "validation", "artifact", "manifest"]):
            return RetryDecision("human_review", 0, "validation_fail")

        if any(x in code for x in ["policy", "blocked", "forbidden", "fatal"]):
            return RetryDecision("block", 0, "fatal_error")

        return RetryDecision("retry", 1, "unknown_retryable")
```

Giai đoạn đầu có thể chỉ dùng policy này trong `_execute_stage()` để ghi incident/retry reason, chưa cần thay toàn bộ retry engine.
