import { NextRequest, NextResponse } from "next/server";
import {
  AutoIndustryDetector,
  AutoFunnelGenerator,
  FunnelGenerateRequestSchema,
} from "@/lib/scale-intelligence";

export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    const validated = FunnelGenerateRequestSchema.parse(payload);

    const detected = new AutoIndustryDetector().detect({
      text: `${validated.product_name} ${validated.industry} ${validated.pain_point}`,
      product_name: validated.product_name,
      image_description: validated.desired_outcome,
      metadata: {},
    });

    const funnel = new AutoFunnelGenerator().generate(validated);

    return NextResponse.json({
      industry_detection: detected,
      funnel,
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
