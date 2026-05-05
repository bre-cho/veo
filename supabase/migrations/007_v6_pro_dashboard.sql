create table if not exists public.campaigns (
  id uuid primary key,
  industry text not null,
  goal text not null,
  input jsonb not null default '{}'::jsonb,
  brain jsonb not null default '{}'::jsonb,
  variants jsonb not null default '{}'::jsonb,
  winner jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.winner_dna (
  id uuid primary key,
  campaign_id uuid references public.campaigns(id) on delete cascade,
  type text not null,
  hook text,
  offer text,
  cta text,
  prompt text not null,
  score jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_campaigns_created_at on public.campaigns(created_at desc);
create index if not exists idx_campaigns_industry on public.campaigns(industry);
create index if not exists idx_winner_dna_created_at on public.winner_dna(created_at desc);