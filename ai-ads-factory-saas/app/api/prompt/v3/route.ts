import { NextResponse } from "next/server";
import { generatePromptV3 } from "@/lib/prompt/prompt-engine-v3";

export async function POST(req: Request) {
  const { input, design } = await req.json();
  const variants = generatePromptV3(input, design);
  return NextResponse.json({ top3: variants.slice(0, 3), all: variants });
}
