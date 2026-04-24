# model import registry patch

## Option A — repo có `backend/app/models/__init__.py`

Thêm đúng 1 dòng:

```python
import app.drama.models  # noqa: F401
```

## Option B — repo có `backend/app/db/base.py`

Thêm gần các model imports khác:

```python
import app.drama.models  # noqa: F401
```

## Option C — repo dùng explicit model list

Thêm các model này:

```python
from app.drama.models import (  # noqa: F401
    DramaArcProgress,
    DramaCharacterProfile,
    DramaCharacterState,
    DramaRelationshipEdge,
    DramaMemoryTrace,
    DramaSceneDramaState,
)
```

Mục tiêu duy nhất: đảm bảo Drama SQLAlchemy models được import trước khi Alembic đọc `Base.metadata`.
