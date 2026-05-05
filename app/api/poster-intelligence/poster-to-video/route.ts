import { NextRequest, NextResponse } from "next/server";
import { AutoVideoFromPoster, PosterToVideoRequestSchema } from "@/lib/poster-intelligence";

export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    const validated = PosterToVideoRequestSchema.parse(payload);
    const result = new AutoVideoFromPoster().build(validated);
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
