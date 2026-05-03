import { NextResponse } from "next/server";
import { z } from "zod";
import { createDeployAuditLog } from "@/lib/v7/audit";
import { validateApprovalToken } from "@/lib/v7/approval-token";
import { getCampaign } from "@/lib/v6-pro/repository";
import { mapWinnerToMetaDraft, mapWinnerToTikTokDraft } from "@/lib/v7/draft-mapper";

const PublishSchema = z
  .object({
    approval_token: z.string().min(1),
    campaign_id: z.string().uuid().optional(),
    winner: z
      .object({
        type: z.string().min(1),
        hook: z.string().min(1),
        offer: z.string().min(1),
        cta: z.string().min(1),
        prompt: z.string().min(1)
      })
      .optional(),
    goal: z.string().optional(),
    brand: z.string().optional(),
    budget_daily: z.number().int().positive().optional(),
    platforms: z.array(z.enum(["meta", "tiktok"])).default(["meta", "tiktok"]),
    confirm_live: z.boolean().default(false)
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

async function publishMetaDraft(payload: ReturnType<typeof mapWinnerToMetaDraft>) {
  const accessToken = process.env.META_GRAPH_ACCESS_TOKEN;
  const adAccountId = process.env.META_AD_ACCOUNT_ID;

  if (!accessToken || !adAccountId) {
    return {
      ok: false,
      status: "skipped",
      reason: "Missing META_GRAPH_ACCESS_TOKEN or META_AD_ACCOUNT_ID"
    };
  }

  // Keep first live publish safe: create campaign in paused status only.
  const response = await fetch(`https://graph.facebook.com/v22.0/act_${adAccountId}/campaigns`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      name: payload.campaign.name,
      objective: payload.campaign.objective,
      status: payload.campaign.status,
      special_ad_categories: payload.campaign.special_ad_categories,
      access_token: accessToken
    })
  });

  const data = await response.json();
  return {
    ok: response.ok,
    status: response.ok ? "published" : "error",
    data
  };
}

async function publishTikTokDraft(payload: ReturnType<typeof mapWinnerToTikTokDraft>) {
  const accessToken = process.env.TIKTOK_ACCESS_TOKEN;
  const advertiserId = process.env.TIKTOK_ADVERTISER_ID;

  if (!accessToken || !advertiserId) {
    return {
      ok: false,
      status: "skipped",
      reason: "Missing TIKTOK_ACCESS_TOKEN or TIKTOK_ADVERTISER_ID"
    };
  }

  const response = await fetch("https://business-api.tiktok.com/open_api/v1.3/campaign/create/", {
    method: "POST",
    headers: {
      "Access-Token": accessToken,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      advertiser_id: advertiserId,
      campaign_name: payload.campaign.campaign_name,
      objective_type: payload.campaign.objective_type,
      budget_mode: payload.campaign.budget_mode,
      budget: payload.campaign.budget
    })
  });

  const data = await response.json();
  const ok = response.ok && data?.code === 0;
  return {
    ok,
    status: ok ? "published" : "error",
    data
  };
}

export async function POST(req: Request) {
  let campaignId: string | null = null;

  try {
    const payload = PublishSchema.parse(await req.json());

    if (!payload.confirm_live) {
      return NextResponse.json({ error: "confirm_live must be true" }, { status: 400 });
    }

    const approval = validateApprovalToken(payload.approval_token);
    if (!approval.ok) {
      await createDeployAuditLog({
        campaignId: payload.campaign_id || null,
        action: "publish_denied",
        platform: payload.platforms.join(","),
        mode: "live",
        status: "error",
        actor: "dashboard",
        request: {
          campaign_id: payload.campaign_id || null,
          platforms: payload.platforms,
          confirm_live: payload.confirm_live
        },
        response: {
          reason: approval.reason || "Invalid approval token"
        }
      });

      return NextResponse.json({ error: approval.reason || "Invalid approval token" }, { status: 403 });
    }

    let winner = payload.winner || null;
    let goal = payload.goal || "conversion";
    let brand = payload.brand || "AI Ads Factory";
    campaignId = payload.campaign_id || crypto.randomUUID();

    if (!winner && payload.campaign_id) {
      const campaign = await getCampaign(payload.campaign_id);
      if (!campaign?.winner) {
        return NextResponse.json({ error: "Campaign winner not found" }, { status: 404 });
      }
      winner = campaign.winner;
      goal = String(campaign.goal || goal);
      brand = String(campaign.input?.brand || campaign.input?.brand_name || brand);
      campaignId = String(campaign.id || campaignId);
    }

    if (!winner) {
      return NextResponse.json({ error: "Missing winner" }, { status: 400 });
    }

    const metaDraft = payload.platforms.includes("meta")
      ? mapWinnerToMetaDraft({ winner, campaignId, goal, brand, budgetDaily: payload.budget_daily })
      : null;
    const tiktokDraft = payload.platforms.includes("tiktok")
      ? mapWinnerToTikTokDraft({ winner, campaignId, goal, brand, budgetDaily: payload.budget_daily })
      : null;

    const [metaResult, tiktokResult] = await Promise.all([
      metaDraft ? publishMetaDraft(metaDraft) : Promise.resolve(null),
      tiktokDraft ? publishTikTokDraft(tiktokDraft) : Promise.resolve(null)
    ]);

    const responsePayload = {
      ok: true,
      mode: "live",
      campaign_id: campaignId,
      published_at: new Date().toISOString(),
      results: {
        meta: metaResult,
        tiktok: tiktokResult
      },
      safety: {
        approval_token_required: true,
        confirm_live_required: true
      }
    };

    await createDeployAuditLog({
      campaignId,
      action: "publish_attempt",
      platform: payload.platforms.join(","),
      mode: "live",
      status: "ok",
      actor: "dashboard",
      request: {
        campaign_id: campaignId,
        platforms: payload.platforms,
        budget_daily: payload.budget_daily || null,
        confirm_live: payload.confirm_live
      },
      response: responsePayload as unknown as Record<string, unknown>
    });

    return NextResponse.json({
      ...responsePayload,
      safety: {
        ...responsePayload.safety,
        approval_mode: approval.mode,
        approval_expires_at: approval.expiresAt ? new Date(approval.expiresAt).toISOString() : null
      }
    });
  } catch (error: any) {
    try {
      await createDeployAuditLog({
        campaignId,
        action: "publish_failed",
        platform: "unknown",
        mode: "live",
        status: "error",
        actor: "dashboard",
        request: {
          campaign_id: campaignId
        },
        response: {
          message: error.message || "Publish failed"
        }
      });
    } catch {
      // Ignore secondary logging errors.
    }

    if (error?.name === "ZodError") {
      return NextResponse.json({ error: "Invalid payload", details: error.issues }, { status: 400 });
    }
    return NextResponse.json({ error: error.message || "Publish failed" }, { status: 500 });
  }
}