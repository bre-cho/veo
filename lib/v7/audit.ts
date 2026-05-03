import { createSupabaseServiceClient } from "@/lib/supabase/server";

type DeployAuditRecord = {
  id: string;
  campaign_id: string | null;
  action: string;
  platform: string;
  mode: "draft" | "live";
  status: "ok" | "error";
  actor: string;
  request: Record<string, unknown>;
  response: Record<string, unknown> | null;
  created_at: string;
};

const memory = {
  logs: [] as DeployAuditRecord[]
};

function hasSupabasePersistence() {
  return Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY);
}

function nextId() {
  return crypto.randomUUID();
}

export async function createDeployAuditLog(args: {
  campaignId?: string | null;
  action: string;
  platform: string;
  mode: "draft" | "live";
  status: "ok" | "error";
  actor?: string;
  request: Record<string, unknown>;
  response?: Record<string, unknown> | null;
}) {
  const record: DeployAuditRecord = {
    id: nextId(),
    campaign_id: args.campaignId || null,
    action: args.action,
    platform: args.platform,
    mode: args.mode,
    status: args.status,
    actor: args.actor || "system",
    request: args.request,
    response: args.response || null,
    created_at: new Date().toISOString()
  };

  if (!hasSupabasePersistence()) {
    memory.logs.unshift(record);
    return record;
  }

  const supabase = createSupabaseServiceClient();
  const { data, error } = await supabase.from("v7_deploy_audit_logs").insert(record).select("*").single();

  if (error) {
    const missingTable = error.message.toLowerCase().includes("v7_deploy_audit_logs");
    if (missingTable) {
      memory.logs.unshift(record);
      return record;
    }
  }

  if (error || !data) {
    throw new Error(error?.message || "Cannot save deploy audit log");
  }

  return data as DeployAuditRecord;
}

export async function listDeployAuditLogs(limit = 50) {
  if (!hasSupabasePersistence()) {
    return memory.logs.slice(0, limit);
  }

  const supabase = createSupabaseServiceClient();
  const { data, error } = await supabase
    .from("v7_deploy_audit_logs")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(limit);

  if (error) {
    const missingTable = error.message.toLowerCase().includes("v7_deploy_audit_logs");
    if (missingTable) {
      return memory.logs.slice(0, limit);
    }
    throw new Error(error.message);
  }

  return data || [];
}