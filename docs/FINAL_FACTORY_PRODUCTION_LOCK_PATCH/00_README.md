# FINAL FACTORY PRODUCTION LOCK PATCH

Mục tiêu của thư mục này là hướng dẫn dev hoàn thiện `veo-main-9` thành **AI Video Factory vận hành khép kín**.

Patch này không thêm tính năng lan man. Nó khóa 4 điểm cuối:

1. **EXECUTE_RENDER phải tạo và xác nhận artifact thật**
2. **QA_VALIDATE phải kiểm artifact/manifest/audio/subtitle/duration/SEO/publish readiness thật**
3. **PUBLISH phải có approval gate rõ ràng: dry_run → approved_publish → live**
4. **CI phải khóa regression: quick verify nhanh, factory dry-run E2E, i18n, artifact validator**

## Tư duy vận hành

Toàn bộ hệ phải chạy như nhà máy khép kín:

```txt
INPUT
→ INTAKE
→ CONTEXT_LOAD
→ SKILL_ROUTE
→ SCRIPT_PLAN
→ SCENE_BUILD
→ AVATAR_AUDIO_BUILD
→ RENDER_PLAN
→ EXECUTE_RENDER
→ QA_VALIDATE
→ SEO_PACKAGE
→ PUBLISH
→ TELEMETRY_LEARN
→ MEMORY
```

Không để render/audio/avatar/SEO/publish tự chạy rời rạc trong production. Mọi job video dài phải có `FactoryRun` để trace, audit, retry, QA và learning.

## Patch name

```txt
FINAL_FACTORY_PRODUCTION_LOCK_PATCH
```

## Làm theo thứ tự

1. Đọc `01_ARCHITECTURE_FACTORY_OS.md`
2. Làm theo `02_PATCH_ORDER.md`
3. Copy code theo `03_BACKEND_CODE_GUIDE.md`
4. Sửa frontend theo `04_FRONTEND_GUIDE.md`
5. Chạy checklist trong `05_CI_VERIFY_CHECKLIST.md`
6. So file theo `06_FILE_BY_FILE_PATCH_MAP.md`
7. Chỉ merge khi đạt `07_ACCEPTANCE_CRITERIA.md`


## Bổ sung mới

- `08_FRONTEND_100_PERCENT_VIETNAMESE_PATCH.md` — hướng dẫn khóa 100% giao diện frontend tiếng Việt, bổ sung dictionary, CI i18n guard và acceptance criteria.
