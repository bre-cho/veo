import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    status: "ok",
    modules: [
      "qa_auto_check_system",
      "auto_fix_poster_ai",
      "live_ctr_optimizer",
      "auto_video_from_poster",
    ],
  });
}
