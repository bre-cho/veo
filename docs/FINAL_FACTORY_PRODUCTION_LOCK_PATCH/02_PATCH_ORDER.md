# 02 — Patch Order

Làm đúng thứ tự sau để tránh patch nhiều lần.

## Phase 1 — Lock EXECUTE_RENDER

Thêm:

```txt
backend/app/factory/factory_render_completion.py
backend/app/factory/factory_artifact_validator.py
```

Sửa:

```txt
backend/app/factory/factory_orchestrator.py
backend/app/factory/factory_qa_verifier.py
```

Mục tiêu:

```txt
render dispatch xong phải biết artifact có tồn tại hay chưa
production không được coi render là success nếu artifact missing
```

## Phase 2 — Lock QA_VALIDATE

Nâng QA từ metadata-check thành artifact-check:

```txt
video artifact exists/readable
manifest parse OK
scene count match
audio exists hoặc explicit no-audio policy
subtitle segments valid
duration > 0
SEO package readiness
publish payload readiness
```

## Phase 3 — Lock Publish Approval

Thêm:

```txt
backend/app/factory/factory_publish_control.py
```

Sửa:

```txt
backend/app/api/factory.py
backend/app/factory/factory_orchestrator.py
backend/app/models/factory_run.py nếu cần thêm field
```

Flow:

```txt
dry_run mặc định
approve_publish API cập nhật run.extras/policy
publish live chỉ chạy sau approval
```

## Phase 4 — Retry Policy

Thêm:

```txt
backend/app/factory/factory_retry_policy.py
```

Chuẩn hóa:

```txt
transient_error → retry
infra_error → retry limited
validation_fail → human_review/downgrade
fatal_error → block
```

## Phase 5 — Frontend Factory Command Center

Sửa:

```txt
frontend/src/app/factory/page.tsx
frontend/src/components/factory/*
frontend/src/i18n/vi.ts
frontend/src/i18n/en.ts
```

UI cần có:

```txt
video preview
audio preview
subtitle preview
QA detail
SEO preview
publish payload
approve publish
retry stage
incident panel
memory output
```

## Phase 6 — CI Lock

Sửa/thêm:

```txt
.github/workflows/unified-runtime-check.yml
backend/tests/test_factory_artifact_validator.py
backend/tests/test_factory_publish_control.py
backend/tests/test_factory_dry_run_e2e.py
scripts/ci/check_frontend_i18n.py
```

CI phải bắt buộc pass trước merge.
