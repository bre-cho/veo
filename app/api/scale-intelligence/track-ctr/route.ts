import { NextRequest, NextResponse } from "next/server";
import {
  CTRTrackingEventSchema,
  RealCTRDataEngine,
} from "@/lib/scale-intelligence";

export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    const validated = CTRTrackingEventSchema.parse(payload);
    const result = new RealCTRDataEngine().track(validated);
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
