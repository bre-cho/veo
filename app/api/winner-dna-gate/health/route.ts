import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    status: "ok",
    modules: ["winner_dna_recall", "industry_match", "publish_gate"],
  });
}
