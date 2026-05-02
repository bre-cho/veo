create type plan_type as enum ('free','creator','pro','studio');
create type job_status as enum ('queued','processing','completed','failed');

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  plan plan_type default 'free',
  credits int default 10,
  stripe_customer_id text,
  created_at timestamptz default now()
);

create table public.generation_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  prompt text not null,
  status job_status default 'queued',
  result_urls text[] default '{}',
  error text,
  created_at timestamptz default now()
);

create table public.credit_transactions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  amount int not null,
  reason text not null,
  job_id uuid references public.generation_jobs(id) on delete set null,
  created_at timestamptz default now()
);

alter table profiles enable row level security;
alter table generation_jobs enable row level security;
alter table credit_transactions enable row level security;

create policy "profiles owner read" on profiles for select using (auth.uid() = id);
create policy "jobs owner all" on generation_jobs for all using (auth.uid() = user_id);
create policy "credit tx owner read" on credit_transactions for select using (auth.uid() = user_id);

create index generation_jobs_status_created_at_idx on public.generation_jobs(status, created_at);
create index credit_transactions_user_created_at_idx on public.credit_transactions(user_id, created_at desc);

create or replace function public.add_credits(
  p_user_id uuid,
  p_amount int,
  p_reason text
)
returns int
language plpgsql
security definer
as $$
declare
  updated_credits int;
begin
  if p_amount <= 0 then
    raise exception 'amount must be positive';
  end if;

  update public.profiles
  set credits = credits + p_amount
  where id = p_user_id
  returning credits into updated_credits;

  if updated_credits is null then
    raise exception 'profile not found';
  end if;

  insert into public.credit_transactions(user_id, amount, reason)
  values (p_user_id, p_amount, p_reason);

  return updated_credits;
end;
$$;

create or replace function public.deduct_credits(
  p_user_id uuid,
  p_amount int,
  p_reason text,
  p_job_id uuid default null
)
returns int
language plpgsql
security definer
as $$
declare
  updated_credits int;
begin
  if p_amount <= 0 then
    raise exception 'amount must be positive';
  end if;

  update public.profiles
  set credits = credits - p_amount
  where id = p_user_id and credits >= p_amount
  returning credits into updated_credits;

  if updated_credits is null then
    raise exception 'insufficient credits or profile not found';
  end if;

  insert into public.credit_transactions(user_id, amount, reason, job_id)
  values (p_user_id, -p_amount, p_reason, p_job_id);

  return updated_credits;
end;
$$;
