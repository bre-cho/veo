import { NextRequest, NextResponse } from "next/server";
import { PresetLibrary } from "@/lib/preset-library";

const library = new PresetLibrary();

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const industry = searchParams.get("industry") || undefined;
  const engine = searchParams.get("engine") || undefined;

  const templates = library.list(industry || undefined, engine || undefined);
  return NextResponse.json(templates);
}
