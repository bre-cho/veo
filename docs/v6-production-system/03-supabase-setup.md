# 03 — Supabase Setup

1. Create Supabase project.
2. Copy env:

```env
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
```

3. Run SQL:

```sql
-- use file:
supabase/migrations/003_v6_production.sql
```

Tables:

- poster_projects
- ad_metrics

RLS enabled.
