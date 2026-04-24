# Drama App Integration Patch

Pack này nối FULL MONOREPO DRAMA PATCH vào app thật.

## Files

- `patches/api_router_patch.md` — patch 3–5 dòng cho `api_router.py`
- `patches/main_py_patch.md` — fallback patch nếu router nằm trong `main.py`
- `backend/app/drama/api/__init__.py` — router registry
- `backend/app/drama/models/__init__.py` — model registry cho Alembic
- `patches/model_registry_patch.md` — nơi thêm model imports
- `patches/alembic_env_patch.md` — target metadata hookup
- `scripts/smoke_drama_stack.sh` — smoke test 1 lệnh
- `smoke_test_one_command.md` — hướng dẫn chạy smoke test

## Merge order

1. Copy `backend/app/drama/api/__init__.py`
2. Copy `backend/app/drama/models/__init__.py`
3. Apply `api_router.py` patch hoặc `main.py` patch, chọn đúng 1
4. Apply model registry patch
5. Apply Alembic env patch
6. Run Alembic autogenerate + upgrade
7. Run smoke test script

## Important

Không dùng đồng thời `api_router.py patch` và `main.py patch` nếu cả hai cùng include vào app, tránh duplicate routes.
