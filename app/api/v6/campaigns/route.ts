import { NextResponse } from "next/server";
import { listCampaigns } from "@/lib/v6-pro/repository";

export async function GET() {
  try {
    const campaigns = await listCampaigns();
    return NextResponse.json({ ok: true, campaigns });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || "Cannot load campaigns" }, { status: 500 });
  }
}