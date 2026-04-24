# Alembic target metadata hookup

## Case phổ biến

Trong `backend/alembic/env.py`, đảm bảo có import Base và drama models trước `target_metadata`:

```python
from app.db.base_class import Base
import app.drama.models  # noqa: F401

target_metadata = Base.metadata
```

## Nếu repo dùng `app.db.base import Base`

```python
from app.db.base import Base
import app.drama.models  # noqa: F401

target_metadata = Base.metadata
```

## Nếu repo đã có `target_metadata = Base.metadata`

Chỉ thêm dòng này phía trên:

```python
import app.drama.models  # noqa: F401
```

## Verify nhanh

```bash
cd backend
alembic revision --autogenerate -m "add drama engine tables"
alembic upgrade head
```

Nếu autogenerate không thấy table `drama_*`, nghĩa là model registry chưa được import vào Alembic runtime.
