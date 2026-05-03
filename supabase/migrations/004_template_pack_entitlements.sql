create table if not exists public.template_pack_entitlements (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  pack_slug text not null,
  stripe_session_id text,
  stripe_payment_intent_id text,
  amount_paid numeric default 0,
  currency text default 'vnd',
  created_at timestamptz default now(),
  unique(user_id, pack_slug)
);

alter table public.template_pack_entitlements enable row level security;

drop policy if exists "template_pack_entitlements owner read" on public.template_pack_entitlements;
create policy "template_pack_entitlements owner read"
on public.template_pack_entitlements
for select
using (auth.uid() = user_id);
