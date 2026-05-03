import { NextResponse } from "next/server";
import { z } from "zod";
import { getCampaign } from "@/lib/v6-pro/repository";
import { createDeployAuditLog } from "@/lib/v7/audit";
import { mapWinnerToMetaDraft, mapWinnerToTikTokDraft } from "@/lib/v7/draft-mapper";

const WinnerSchema = z.object({
  type: z.string().min(1),
  hook: z.string().min(1),
  offer: z.string().min(1),
  cta: z.string().min(1),
  prompt: z.string().min(1),
  score: z
    .object({
      total: z.number().optional(),
      attention: z.number().optional(),
      trust: z.number().optional(),
      conversion: z.number().optional(),
      visual: z.number().optional()
    })
    .optional()
});

const DraftSchema = z
  .object({
    campaign_id: z.string().uuid().optional(),
    winner: WinnerSchema.optional(),
    goal: z.string().optional(),
    brand: z.string().optional(),
    budget_daily: z.number().int().positive().optional(),
    platforms: z.array(z.enum(["meta", "tiktok"])).default(["meta", "tiktok"])
  })
  .superRefine((data, ctx) => {
    if (!data.campaign_id && !data.winner) {
      ctx.addIssue({
        path: ["winner"],
        code: z.ZodIssueCode.custom,
        message: "Provide campaign_id or winner"
      });
    }
  });

export async function POST(req: Request) {
  try {
    const payload = DraftSchema.parse(await req.json());

    let winner = payload.winner || null;
    let goal = payload.goal || "conversion";
    let brand = payload.brand || "AI Ads Factory";
    let campaignId = payload.campaign_id || crypto.randomUUID();

    if (!winner && payload.campaign_id) {
      const campaign = await getCampaign(payload.campaign_id);
      if (!campaign?.winner) {
        return NextResponse.json({ error: "Campaign winner not found" }, { status: 404 });
      }
      winner = WinnerSchema.parse(campaign.winner);
      goal = String(campaign.goal || goal);
      brand = String(campaign.input?.brand || campaign.input?.brand_name || brand);
      campaignId = String(campaign.id || campaignId);
    }

    if (!winner) {
      return NextResponse.json({ error: "Missing winner" }, { status: 400 });
    }

    const draft = {
      mode: "draft" as const,
      campaign_id: campaignId,
      source: "winner-dna",
      generated_at: new Date().toISOString(),
      platforms: payload.platforms,
      payloads: {
        meta: payload.platforms.includes("meta")
          ? mapWinnerToMetaDraft({
              winner,
              campaignId,
              goal,
              brand,
              budgetDaily: payload.budget_daily
            })
          : null,
        tiktok: payload.platforms.includes("tiktok")
          ? mapWinnerToTikTokDraft({
              winner,
              campaignId,
              goal,
              brand,
              budgetDaily: payload.budget_daily
            })
          : null
      },
      safety: {
        spend_enabled: false,
        approval_required: true,
        note: "Draft only. No live spend without manual approval."
      }
    };

    await createDeployAuditLog({
      campaignId,
      action: "draft_created",
      platform: payload.platforms.join(","),
      mode: "draft",
      status: "ok",
      actor: "dashboard",
      request: {
        campaign_id: payload.campaign_id || null,
        platforms: payload.platforms,
        budget_daily: payload.budget_daily || null
      },
      response: {
        generated_at: draft.generated_at,
        source: draft.source
      }
    });

    return NextResponse.json({ ok: true, draft });
  } catch (error: any) {
    if (error?.name === "ZodError") {
      return NextResponse.json({ error: "Invalid payload", details: error.issues }, { status: 400 });
    }
    return NextResponse.json({ error: error.message || "Create draft failed" }, { status: 500 });
  }
}