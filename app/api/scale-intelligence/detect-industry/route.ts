import { NextRequest, NextResponse } from "next/server";
import {
  AutoIndustryDetector,
  IndustryDetectRequestSchema,
} from "@/lib/scale-intelligence";

export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    const validated = IndustryDetectRequestSchema.parse(payload);
    const result = new AutoIndustryDetector().detect(validated);
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
