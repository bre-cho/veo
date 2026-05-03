create table if not exists public.poster_projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  name text not null,
  document jsonb not null default '{}',
  prompt_result jsonb not null default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.ad_metrics (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  campaign_name text,
  spend numeric default 0,
  impressions int default 0,
  clicks int default 0,
  leads int default 0,
  sales int default 0,
  revenue numeric default 0,
  created_at timestamptz default now()
);

alter table public.poster_projects enable row level security;
alter table public.ad_metrics enable row level security;

drop policy if exists "poster_projects owner all" on public.poster_projects;
create policy "poster_projects owner all"
on public.poster_projects
for all
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "ad_metrics owner all" on public.ad_metrics;
create policy "ad_metrics owner all"
on public.ad_metrics
for all
using (auth.uid() = user_id)
with check (auth.uid() = user_id);
