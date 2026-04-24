
# Router Registration Map

Recommended aggregator import:

```python
from app.drama.api import ALL_DRAMA_ROUTERS

for router in ALL_DRAMA_ROUTERS:
    app.include_router(router)
```

## Routers

| Router file | Prefix | Purpose |
|---|---|---|
| backend/app/drama/api/drama_characters.py | /api/v1/drama/characters | Character CRUD + preset/bootstrap |
| backend/app/drama/api/drama_relationships.py | /api/v1/drama/relationships | Directional relationship edge CRUD/upsert |
| backend/app/drama/api/drama_scenes.py | /api/v1/drama/scenes | Analyze scene context and return machine-readable drama payload |
| backend/app/drama/api/drama_compile.py | /api/v1/drama/compile | Compile scene analysis into blocking/camera/render-bridge payload |
| backend/app/drama/api/drama_arcs.py | /api/v1/drama/arcs | Arc read/advance surface |
| backend/app/drama/api/drama_memory.py | /api/v1/drama/memory | Read/query memory traces and recall suggestions |
| backend/app/drama/api/drama_state.py | /api/v1/drama/state | Read aggregated drama state |
| backend/app/drama/api/drama_admin.py | /api/v1/drama/admin | Admin recompute / episode repair |

## Suggested app registration order

1. characters
2. relationships
3. scenes
4. compile
5. arcs
6. memory
7. state
8. admin

## Dependency adaptation points

Normalize these imports to your monorepo before enabling routers:

- `from app.api.deps import get_db`
- `from app.db.base_class import Base`
- `from app.db.session import SessionLocal`

If your repo uses another namespace, keep the service contracts and only rewrite the infra imports.
