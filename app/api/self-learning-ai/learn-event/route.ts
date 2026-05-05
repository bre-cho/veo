import { NextRequest, NextResponse } from "next/server";
import {
  AdPerformanceEventSchema,
  WinnerDNALearner,
} from "@/lib/self-learning-ai";

export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    const validated = AdPerformanceEventSchema.parse(payload);
    const result = await new WinnerDNALearner().learnEvent(validated);
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
