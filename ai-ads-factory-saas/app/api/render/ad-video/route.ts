import { NextResponse } from "next/server";
import { renderAdVideo } from "@/lib/render/remotion-render";
import { createSupabaseServiceClient } from "@/lib/supabase/server";
import { chargeCredits, ensureProfile } from "@/lib/billing/credits";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(req: Request) {
  const { ad, design, userId, mode } = await req.json();

  if (mode === "queue") {
    if (userId) {
      try {
        await ensureProfile(userId);
        await chargeCredits(userId, 1, "Video render queue");
      } catch (error) {
        return NextResponse.json(
          { error: "Insufficient credits", detail: String(error) },
          { status: 402 }
        );
      }
    }

    const supabase = createSupabaseServiceClient();
    const payload = JSON.stringify({ ad, design });

    const { data, error } = await supabase
      .from("generation_jobs")
      .insert({ user_id: userId || null, prompt: payload, status: "queued" })
      .select("id")
      .single();

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json({ queued: true, jobId: data.id });
  }

  const url = await renderAdVideo({
    hook: ad.hook,
    headline: ad.headline,
    cta: ad.cta,
    primary: design.colors.primary,
    accent: design.colors.accent,
    highlight: design.colors.highlight || design.colors.accent
  });

  return NextResponse.json({ url });
}
