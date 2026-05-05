import { NextRequest, NextResponse } from "next/server";
import { HeatmapClickPredictor } from "@/lib/self-learning-ai";

export async function POST(req: NextRequest) {
  try {
    const payload = (await req.json()) as Record<string, unknown>;
    const result = new HeatmapClickPredictor().predict(payload);
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
