import { NextRequest, NextResponse } from "next/server";
import { WinnerDNALoader } from "@/lib/winner-dna-gate";

interface RouteContext {
  params: Promise<{ industry: string }>;
}

export async function GET(_req: NextRequest, { params }: RouteContext) {
  const { industry } = await params;
  const winners = new WinnerDNALoader().byIndustry(industry);

  return NextResponse.json({
    industry,
    winners,
  });
}
