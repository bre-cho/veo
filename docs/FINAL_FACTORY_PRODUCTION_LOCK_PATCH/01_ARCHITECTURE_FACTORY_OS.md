# 01 — Architecture: Closed-Loop AI Video Factory OS

## Hiện trạng `veo-main-9`

Factory OS đã có xương sống:

```txt
backend/app/factory/factory_orchestrator.py
backend/app/factory/factory_render_adapter.py
backend/app/factory/factory_qa_verifier.py
backend/app/api/factory.py
backend/app/workers/factory_worker.py
frontend/src/app/factory/page.tsx
```

Nhưng còn thiếu khóa production:

```txt
render_job_id có thể có nhưng video artifact chưa chắc tồn tại
QA hiện chủ yếu kiểm metadata, chưa kiểm file artifact thật
PUBLISH chưa ép approval rõ ràng
Retry chưa có phân loại lỗi chuẩn
Frontend Factory chưa đủ command center
CI chưa khóa factory dry-run E2E end-to-end
```

## Kiến trúc sau patch

```txt
FactoryOrchestrator
  ├─ FactoryRenderAdapter
  ├─ FactoryRenderCompletionWatcher      NEW
  ├─ FactoryArtifactValidator            NEW
  ├─ FactoryRetryPolicy                  NEW
  ├─ FactoryPublishApprovalService       NEW
  ├─ FactoryQAVerifier                   UPGRADE
  ├─ FactoryMemory
  └─ FactoryMetrics
```

## Luồng chuẩn production

```txt
EXECUTE_RENDER
  → build manifest
  → persist RenderJob + RenderSceneTask
  → dispatch render task
  → wait/poll completion nếu mode sync hoặc verify-after-dispatch
  → fetch final_video_url/output_url/storage_key
  → validate artifact exists/readable
  → fail stage nếu artifact missing trong production

QA_VALIDATE
  → artifact validator
  → manifest validator
  → audio/subtitle/duration validator
  → SEO readiness validator
  → publish readiness validator

SEO_PACKAGE
  → chỉ chạy khi QA artifact cơ bản pass
  → nhận render artifact thật từ RenderJob

PUBLISH
  → mặc định dry_run
  → live publish chỉ khi approved_publish=true
  → auto publish chỉ khi flag riêng bật

TELEMETRY_LEARN
  → lưu winner/failure DNA
  → lưu retry/failure pattern
  → lưu SEO/render/publish metrics
```

## Core law

```txt
NO ARTIFACT  → NO QA PASS
NO QA PASS   → NO SEO FINAL
NO APPROVAL  → NO LIVE PUBLISH
NO TRACE     → NO PRODUCTION RUN
NO CI PASS   → NO MERGE
```
