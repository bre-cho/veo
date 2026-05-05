import { NextRequest, NextResponse } from "next/server";
import {
  AutoFunnelGenerator,
  FunnelGenerateRequestSchema,
} from "@/lib/scale-intelligence";

export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    const validated = FunnelGenerateRequestSchema.parse(payload);
    const result = new AutoFunnelGenerator().generate(validated);
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
