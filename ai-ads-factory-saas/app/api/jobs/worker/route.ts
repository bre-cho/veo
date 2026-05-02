import { NextResponse } from "next/server";
import { createSupabaseServiceClient } from "@/lib/supabase/server";
import { renderAdVideo } from "@/lib/render/remotion-render";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST() {
  const supabase = createSupabaseServiceClient();

  const { data: job, error: fetchError } = await supabase
    .from("generation_jobs")
    .select("id, prompt")
    .eq("status", "queued")
    .order("created_at", { ascending: true })
    .limit(1)
    .maybeSingle();

  if (fetchError) return NextResponse.json({ error: fetchError.message }, { status: 500 });
  if (!job) return NextResponse.json({ ok: true, message: "No queued job" });

  await supabase.from("generation_jobs").update({ status: "processing" }).eq("id", job.id);

  try {
    const payload = JSON.parse(job.prompt || "{}");
    const ad = payload.ad || {};
    const design = payload.design || { colors: {} };

    const url = await renderAdVideo({
      hook: ad.hook || "Hook",
      headline: ad.headline || "Headline",
      cta: ad.cta || "Call to action",
      primary: design.colors?.primary || "#0A0F2C",
      accent: design.colors?.accent || "#2563EB",
      highlight: design.colors?.highlight || design.colors?.accent || "#FACC15"
    });

    await supabase
      .from("generation_jobs")
      .update({ status: "completed", result_urls: [url], error: null })
      .eq("id", job.id);

    return NextResponse.json({ ok: true, jobId: job.id, url });
  } catch (error) {
    await supabase
      .from("generation_jobs")
      .update({ status: "failed", error: String(error) })
      .eq("id", job.id);

    return NextResponse.json({ error: String(error), jobId: job.id }, { status: 500 });
  }
}
