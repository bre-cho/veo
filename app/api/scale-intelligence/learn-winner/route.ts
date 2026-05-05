import { NextRequest, NextResponse } from "next/server";
import {
  WinnerLearningEngine,
  WinnerLearningInputSchema,
} from "@/lib/scale-intelligence";

export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    const validated = WinnerLearningInputSchema.parse(payload);
    const result = await new WinnerLearningEngine().learn(validated);
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
