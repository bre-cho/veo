import { NextRequest, NextResponse } from "next/server";
import { PresetLibrary } from "@/lib/preset-library";

const library = new PresetLibrary();

interface RouteContext {
  params: Promise<{
    id: string;
  }>;
}

export async function GET(
  _req: NextRequest,
  { params }: RouteContext
) {
  const { id } = await params;
  const templateId = decodeURIComponent(id);

  const template = library.get(templateId);
  if (!template) {
    return NextResponse.json({ error: "Template not found" }, { status: 404 });
  }

  return NextResponse.json(template);
}
