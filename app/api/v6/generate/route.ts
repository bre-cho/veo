import { NextResponse } from "next/server";
import { z } from "zod";
import { createCampaignRecord, saveWinnerDNA } from "@/lib/v6-pro/repository";
import { runAdsFactoryV6Pro } from "@/lib/v6-pro/runtime";

const GenerateSchema = z.object({
  product_type: z.string().trim().min(1),
  product_info: z.string().trim().optional(),
  description: z.string().trim().optional(),
  goal: z.string().trim().optional(),
  objective: z.string().trim().optional(),
  brand: z.string().trim().optional(),
  brand_name: z.string().trim().optional(),
  ratio: z.string().trim().optional(),
  style: z.string().trim().optional(),
  emotion: z.string().trim().optional(),
  font: z.string().trim().optional(),
  platform: z.string().trim().optional(),
  cta: z.string().trim().optional()
});

export async function POST(req: Request) {
  try {
    const payload = GenerateSchema.parse(await req.json());
    const result = await runAdsFactoryV6Pro(payload);
    const campaign = await createCampaignRecord(result);

    if (result.winner) {
      await saveWinnerDNA(result.winner, campaign.id);
    }

    return NextResponse.json({
      ok: true,
      campaign_id: campaign.id,
      ...result
    });
  } catch (error: any) {
    if (error?.name === "ZodError") {
      return NextResponse.json({ error: "Invalid payload", details: error.issues }, { status: 400 });
    }

    return NextResponse.json({ ok: false, error: error.message || "V6 Pro generation failed" }, { status: 500 });
  }
}