import { NextRequest, NextResponse } from "next/server";
import { PosterPublishRequestSchema, WinnerDNARecallGate } from "@/lib/winner-dna-gate";

export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    const validated = PosterPublishRequestSchema.parse(payload);
    const result = new WinnerDNARecallGate().evaluate(validated);
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof Error) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
