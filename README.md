# AI Ads Factory SaaS

## Quick start

```bash
cp .env.example .env.local
npm install
npm run dev
```

Open:

- http://localhost:3000
- http://localhost:3000/factory
- http://localhost:3000/studio
- http://localhost:3000/marketplace

Nếu chưa có OPENAI_API_KEY, Factory dùng mock output.

## Patch status

- P0: Auth UI + Supabase session + API guard + Stripe checkout
- P1: Image API + Supabase Storage upload + generation job queue
- P2: TikTok OAuth URL + direct post API + campaign create API

## Notes

- Chạy SQL trong `supabase/migrations/001_init.sql` trước khi dùng job queue.
- Tạo bucket `generated-assets` (hoặc đổi bằng `SUPABASE_ASSET_BUCKET`).
- Không expose `SUPABASE_SERVICE_ROLE_KEY` ở client.
