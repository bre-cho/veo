# 06 — File-by-File Patch Map

## Backend — thêm mới

```txt
backend/app/factory/factory_artifact_validator.py
backend/app/factory/factory_render_completion.py
backend/app/factory/factory_publish_control.py
backend/app/factory/factory_retry_policy.py
backend/tests/test_factory_artifact_validator.py
backend/tests/test_factory_publish_control.py
backend/tests/test_factory_dry_run_e2e.py
backend/tests/test_factory_retry_policy.py
```

## Backend — sửa

```txt
backend/app/factory/factory_orchestrator.py
  - EXECUTE_RENDER: wait completion optional + validate artifact
  - QA_VALIDATE: nhận artifact_validation
  - PUBLISH: dry_run/approval/live split
  - TELEMETRY_LEARN: lưu artifact/QA/publish result

backend/app/factory/factory_qa_verifier.py
  - thêm artifact_validation input
  - artifact issues = QA issues

backend/app/api/factory.py
  - thêm approve_publish endpoint
  - thêm publish endpoint nếu chưa có

backend/scripts/verify_unified_runtime.py
  - quick import-only
  - fast path probe + source scan
  - full DB/router/celery/factory

.github/workflows/unified-runtime-check.yml
  - thêm quick timeout 5s
  - thêm factory dry-run e2e
```

## Frontend — thêm/sửa

```txt
frontend/src/app/factory/page.tsx
frontend/src/components/factory/FactoryArtifactPanel.tsx
frontend/src/components/factory/FactoryQAPanel.tsx
frontend/src/components/factory/FactorySEOPanel.tsx
frontend/src/components/factory/FactoryPublishPanel.tsx
frontend/src/components/factory/FactoryIncidentPanel.tsx
frontend/src/components/factory/FactoryMemoryPanel.tsx
frontend/src/i18n/vi.ts
frontend/src/i18n/en.ts
frontend/src/lib/api.ts
```

## Env cần có

```txt
APP_ENV=development|test|production
FACTORY_RENDER_WAIT_FOR_COMPLETION=0|1
FACTORY_RENDER_WAIT_TIMEOUT_SECONDS=60
FACTORY_PUBLISH_DRY_RUN=1
FACTORY_LIVE_PUBLISH=0
PUBLIC_BASE_URL=https://...
NEXT_PUBLIC_API_BASE_URL=https://.../api/v1
```

## Production hard rules

```txt
APP_ENV=production mà PUBLIC_BASE_URL thiếu hoặc localhost → fail
NODE_ENV=production mà NEXT_PUBLIC_API_BASE_URL thiếu hoặc localhost → fail
FACTORY_LIVE_PUBLISH=1 nhưng chưa approve → block
FACTORY_RENDER_WAIT_FOR_COMPLETION=1 mà artifact missing → fail stage
```
