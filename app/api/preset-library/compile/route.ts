import { NextRequest, NextResponse } from "next/server";
import { PresetLibrary, TemplateRenderRequestSchema } from "@/lib/preset-library";

const library = new PresetLibrary();

export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    const validated = TemplateRenderRequestSchema.parse(payload);
    const result = library.compile_prompt(validated);
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof Error) {
      if (error.message.includes("not found")) {
        return NextResponse.json({ error: error.message }, { status: 404 });
      }
      return NextResponse.json({ error: error.message }, { status: 400 });
    }
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
