# Smoke test — 1 lệnh

## Chạy local

```bash
BASE_URL=http://localhost:8000/api/v1 \
PROJECT_ID=00000000-0000-0000-0000-000000000001 \
bash scripts/smoke_drama_stack.sh
```

## Nếu API cần auth

```bash
TOKEN="$ACCESS_TOKEN" \
BASE_URL=http://localhost:8000/api/v1 \
bash scripts/smoke_drama_stack.sh
```

## Coverage

Script kiểm tra:

1. create character Authority
2. create character Rebel
3. upsert relationship
4. analyze scene
5. compile render bridge
6. persist/recompute scene nếu endpoint có sẵn
7. recall memory
8. recompute episode continuity

## GO

- character create trả JSON có `id`
- relationship upsert không lỗi
- scene analyze trả score/payload
- compile trả blocking/camera/continuity/arc payload
- recall/recompute không crash server

## NO-GO

- route `/drama/...` 404: router chưa register đúng
- Alembic không thấy `drama_*`: model registry chưa import vào env.py
- 500 do `get_db` import: sửa dependency import theo repo thật
