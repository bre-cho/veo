create table if not exists public.v7_deploy_audit_logs (
  id uuid primary key,
  campaign_id uuid,
  action text not null,
  platform text not null,
  mode text not null,
  status text not null,
  actor text not null default 'system',
  request jsonb not null default '{}'::jsonb,
  response jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_v7_deploy_audit_created_at on public.v7_deploy_audit_logs(created_at desc);
create index if not exists idx_v7_deploy_audit_campaign_id on public.v7_deploy_audit_logs(campaign_id);