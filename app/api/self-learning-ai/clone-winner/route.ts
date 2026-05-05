import { NextRequest, NextResponse } from "next/server";
import { CloneRequestSchema, WinnerDNACloner } from "@/lib/self-learning-ai";

export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    const validated = CloneRequestSchema.parse(payload);
    const result = await new WinnerDNACloner().clone(validated);
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
