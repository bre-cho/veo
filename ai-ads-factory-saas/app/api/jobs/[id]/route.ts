import { NextResponse } from "next/server";
import { createSupabaseServiceClient } from "@/lib/supabase/server";

export const runtime = "nodejs";

export async function GET(_: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = createSupabaseServiceClient();

  const { data, error } = await supabase
    .from("generation_jobs")
    .select("id, status, result_urls, error, created_at")
    .eq("id", id)
    .maybeSingle();

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  if (!data) return NextResponse.json({ error: "Job not found" }, { status: 404 });

  return NextResponse.json({ job: data });
}
