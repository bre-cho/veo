# api_router.py patch — 3–5 dòng

> Mục tiêu: đăng ký toàn bộ Drama routers mà không sửa từng router một.

```python
# add near other router imports
from app.drama.api import ALL_DRAMA_ROUTERS

# add after api_router = APIRouter() and existing includes
for router in ALL_DRAMA_ROUTERS:
    api_router.include_router(router, prefix="/drama", tags=["drama"])
```

Nếu repo đang dùng prefix `/api/v1` ở `main.py`, giữ nguyên prefix `/drama` ở đây.  
Nếu repo include `api_router` với prefix `/api/v1`, endpoint cuối sẽ là:

```text
/api/v1/drama/...
```
