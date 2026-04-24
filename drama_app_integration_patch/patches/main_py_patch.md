# main.py patch — fallback nếu repo không có api_router.py

> Chỉ dùng patch này nếu repo include router trực tiếp trong `main.py`.

```python
# add near app/router imports
from app.drama.api import ALL_DRAMA_ROUTERS

# add after app = FastAPI(...)
for router in ALL_DRAMA_ROUTERS:
    app.include_router(router, prefix="/api/v1/drama", tags=["drama"])
```

Không dùng đồng thời với `api_router.py patch`, tránh register route 2 lần.
