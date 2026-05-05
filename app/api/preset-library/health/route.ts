import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    status: "ok",
    library: "beauty_engine_v4_templates",
  });
}
