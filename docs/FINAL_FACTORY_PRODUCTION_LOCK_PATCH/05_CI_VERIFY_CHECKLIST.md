# 05 — CI & Verify Checklist

## Quick verify phải import-only

`quick` không được:

```txt
mkdir
write probe
import pydantic settings nặng
import FastAPI registry
import DB/SQLAlchemy models
import Celery
scan toàn bộ source
```

Quick chỉ được:

```txt
import light_runtime_config
import light_runtime_paths
print OK
exit
```

Command:

```bash
PYTHONPATH=backend timeout 5 python backend/scripts/verify_unified_runtime.py --mode quick
```

## Fast verify

Fast được phép:

```txt
path probe
source scan
hardcoded localhost/path scan
```

Command:

```bash
PYTHONPATH=backend python backend/scripts/verify_unified_runtime.py --mode fast
```

## Full verify

Full được phép:

```txt
DB
Alembic
router
Celery
storage
factory imports
```

Command:

```bash
PYTHONPATH=backend python backend/scripts/verify_unified_runtime.py --mode full
```

## Backend tests cần thêm

```bash
PYTHONPATH=backend pytest backend/tests/test_factory_artifact_validator.py
PYTHONPATH=backend pytest backend/tests/test_factory_publish_control.py
PYTHONPATH=backend pytest backend/tests/test_factory_dry_run_e2e.py
PYTHONPATH=backend pytest backend/tests/test_factory_retry_policy.py
```

## Frontend tests

```bash
cd frontend
npm run typecheck
```

## i18n guard

```bash
python scripts/ci/check_frontend_i18n.py
```

## CI final gate

Không merge nếu một trong các điều kiện fail:

```txt
quick verify > 5s
factory dry-run E2E fail
artifact validator fail
publish approval test fail
frontend typecheck fail
i18n guard fail
alembic multiple heads
```


## Frontend i18n lock

CI phải chạy thêm:

```bash
python scripts/ci/check_frontend_i18n.py
cd frontend && npm run typecheck
```

Không merge nếu còn hardcoded English user-facing trong `frontend/src/app` hoặc `frontend/src/components`.
