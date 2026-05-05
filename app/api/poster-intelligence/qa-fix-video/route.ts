import { NextRequest, NextResponse } from "next/server";
import {
  PosterQAAutoCheck,
  AutoFixPosterAI,
  AutoVideoFromPoster,
  PosterToVideoRequestSchema,
} from "@/lib/poster-intelligence";

export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    const validated = PosterToVideoRequestSchema.parse(payload);

    const qa = new PosterQAAutoCheck().check(validated.poster);
    const fix = new AutoFixPosterAI().fix(validated.poster);
    const video = new AutoVideoFromPoster().build(validated);

    return NextResponse.json({
      qa,
      fix,
      video,
      publish_allowed: qa.pass_qa,
    });
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
