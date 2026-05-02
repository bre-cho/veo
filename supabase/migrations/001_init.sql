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

create table public.design_projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  name text not null,
  design_md jsonb not null default '{}',
  created_at timestamptz default now()
);

create table public.generation_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  project_id uuid references public.design_projects(id) on delete cascade,
  prompt text not null,
  status job_status default 'queued',
  result_urls text[] default '{}',
  error text,
  created_at timestamptz default now()
);

alter table profiles enable row level security;
alter table design_projects enable row level security;
alter table generation_jobs enable row level security;

create policy "profiles owner read" on profiles for select using (auth.uid() = id);
create policy "projects owner all" on design_projects for all using (auth.uid() = user_id);
create policy "jobs owner all" on generation_jobs for all using (auth.uid() = user_id);
