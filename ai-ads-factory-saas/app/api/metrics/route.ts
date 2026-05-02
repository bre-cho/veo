import { NextResponse } from "next/server";
import { createSupabaseServiceClient } from "@/lib/supabase/server";

export const runtime = "nodejs";

export async function GET() {
  const supabase = createSupabaseServiceClient();

  const [profilesResult, jobsResult, creditsResult] = await Promise.all([
    supabase.from("profiles").select("id, plan", { count: "exact", head: false }),
    supabase.from("generation_jobs").select("id, status", { count: "exact", head: false }),
    supabase.from("profiles").select("credits")
  ]);

  if (profilesResult.error) {
    return NextResponse.json({ error: profilesResult.error.message }, { status: 500 });
  }
  if (jobsResult.error) {
    return NextResponse.json({ error: jobsResult.error.message }, { status: 500 });
  }
  if (creditsResult.error) {
    return NextResponse.json({ error: creditsResult.error.message }, { status: 500 });
  }

  const totalUsers = profilesResult.count || 0;
  const totalJobs = jobsResult.count || 0;
  const completedJobs = (jobsResult.data || []).filter((j) => j.status === "completed").length;
  const failedJobs = (jobsResult.data || []).filter((j) => j.status === "failed").length;
  const totalCredits = (creditsResult.data || []).reduce((sum, item) => sum + (item.credits || 0), 0);
  const paidUsers = (profilesResult.data || []).filter((p) => p.plan !== "free").length;

  return NextResponse.json({
    totalUsers,
    paidUsers,
    totalJobs,
    completedJobs,
    failedJobs,
    completionRate: totalJobs > 0 ? Number(((completedJobs / totalJobs) * 100).toFixed(1)) : 0,
    totalCredits
  });
}
