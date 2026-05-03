import { createSupabaseServiceClient } from "@/lib/supabase/server";

export async function ensureProfile(userId: string, email?: string | null) {
  const supabase = createSupabaseServiceClient();

  const { data: existing } = await supabase
    .from("profiles")
    .select("id")
    .eq("id", userId)
    .maybeSingle();

  if (existing?.id) {
    return;
  }

  await supabase.from("profiles").upsert({ id: userId, email: email || null }, { onConflict: "id" });
}

export async function addCredits(userId: string, amount: number, reason: string) {
  const supabase = createSupabaseServiceClient();
  const { data, error } = await supabase.rpc("add_credits", {
    p_user_id: userId,
    p_amount: amount,
    p_reason: reason
  });

  if (error) {
    throw error;
  }

  return data;
}

export async function chargeCredits(userId: string, amount: number, reason: string, jobId?: string) {
  const supabase = createSupabaseServiceClient();
  const { data, error } = await supabase.rpc("deduct_credits", {
    p_user_id: userId,
    p_amount: amount,
    p_reason: reason,
    p_job_id: jobId || null
  });

  if (error) {
    throw error;
  }

  return data;
}
