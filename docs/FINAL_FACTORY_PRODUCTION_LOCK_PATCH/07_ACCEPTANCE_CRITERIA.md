# 07 — Acceptance Criteria

Chỉ coi patch DONE khi đạt toàn bộ tiêu chí dưới đây.

## 1. Factory dry-run E2E

Input:

```txt
topic hoặc script
```

Output phải có:

```txt
FactoryRun completed hoặc blocked có lý do rõ
12 stage có trace
script_plan có title/hook/voiceover
scenes có scene_index/voiceover/visual_prompt/duration/subtitle
avatar_audio có avatar_id và audio metadata hoặc warning rõ
render_plan có strategy/cost/time/mandatory_scenes
execute_render có render_job_id + manifest + artifact_validation
qa_validate có qa_passed/issues/warnings/details
seo_package có title/description/tags
publish có dry_run payload
telemetry_learn có memory summary
```

## 2. Artifact lock

Nếu `FACTORY_RENDER_WAIT_FOR_COMPLETION=1`:

```txt
render output missing → EXECUTE_RENDER fail
manifest invalid → QA fail
video file empty → QA fail
scene mismatch → QA fail
```

## 3. Publish lock

```txt
FACTORY_PUBLISH_DRY_RUN=1 → không live publish
FACTORY_LIVE_PUBLISH=1 + no approval → blocked_pending_approval
approve_publish xong → approved_publish_ready hoặc published
```

## 4. CI lock

```bash
PYTHONPATH=backend timeout 5 python backend/scripts/verify_unified_runtime.py --mode quick
PYTHONPATH=backend python backend/scripts/verify_unified_runtime.py --mode fast
PYTHONPATH=backend pytest backend/tests/test_factory_artifact_validator.py
PYTHONPATH=backend pytest backend/tests/test_factory_publish_control.py
PYTHONPATH=backend pytest backend/tests/test_factory_dry_run_e2e.py
cd frontend && npm run typecheck
python scripts/ci/check_frontend_i18n.py
```

## 5. Frontend lock

Trang `/factory` phải hiển thị bằng tiếng Việt:

```txt
Timeline 12 stage
Artifact render
Kết quả QA
Gói SEO
Payload xuất bản
Nút phê duyệt xuất bản
Nút retry/cancel
Incident
Memory learned
```

## 6. Final definition of done

```txt
INPUT
→ script thật
→ scene thật
→ audio/avatar thật hoặc warning rõ
→ render manifest thật
→ render job thật
→ artifact validation thật
→ QA thật
→ SEO thật
→ publish payload thật
→ approval gate thật
→ telemetry/memory thật
→ CI pass
```


## Acceptance bổ sung: Frontend tiếng Việt 100%

- `locale-store` default `vi`.
- Toàn bộ App Router pages hiển thị tiếng Việt.
- Toàn bộ component điều hành Factory/Render/Avatar/Audio/Marketplace/Wallet/Settings hiển thị tiếng Việt.
- Không còn hardcoded English user-facing ngoài `i18n/en.ts`.
- `python scripts/ci/check_frontend_i18n.py` pass.
