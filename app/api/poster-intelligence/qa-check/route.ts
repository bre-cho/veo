import { NextRequest, NextResponse } from "next/server";
import { PosterQAAutoCheck, PosterInputSchema } from "@/lib/poster-intelligence";

export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    const validated = PosterInputSchema.parse(payload);
    const result = new PosterQAAutoCheck().check(validated);
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
