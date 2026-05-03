import { NextResponse } from "next/server";
import { getCampaign } from "@/lib/v6-pro/repository";

export async function GET(_: Request, context: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await context.params;
    const campaign = await getCampaign(id);

    if (!campaign) {
      return NextResponse.json({ ok: false, error: "Campaign not found" }, { status: 404 });
    }

    return NextResponse.json({ ok: true, campaign });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || "Cannot load campaign" }, { status: 500 });
  }
}