import { NextResponse } from "next/server";
import { z } from "zod";
import { runV6System } from "@/lib/orchestrator-v6";

const V6InputSchema = z.object({
  text: z.string().trim().min(1),
  product: z.string().optional(),
  goal: z.enum(["sale", "lead", "click", "education", "event"]).default("lead"),
  industry: z.string().optional(),
  audience: z.string().optional(),
  hasCollection: z.boolean().optional(),
  hasPackaging: z.boolean().optional()
});

export async function POST(req: Request) {
  try {
    const payload = await req.json();
    const input = V6InputSchema.parse(payload);
    return NextResponse.json(runV6System(input));
  } catch (error: any) {
    if (error?.name === "ZodError") {
      return NextResponse.json({ error: "Invalid payload", details: error.issues }, { status: 400 });
    }

    return NextResponse.json({ error: error.message || "V6 run failed" }, { status: 500 });
  }
}
