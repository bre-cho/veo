import { NextRequest, NextResponse } from "next/server";
import {
  PosterInputSchema,
  PosterQAAutoCheck,
  AutoFixPosterAI,
} from "@/lib/poster-intelligence";
import {
  PosterPublishRequestSchema,
  WinnerDNARecallGate,
} from "@/lib/winner-dna-gate";
import {
  AdPerformanceEventSchema,
  WinnerDNALearner,
} from "@/lib/self-learning-ai";

type PublishChainRequest = {
  poster: unknown;
  campaign_id?: string;
  variant_id?: string;
  metrics?: {
    impressions?: number;
    clicks?: number;
    leads?: number;
    sales?: number;
    spend?: number;
    revenue?: number;
    predicted_score?: number;
  };
  auto_fix_if_qa_fail?: boolean;
};

export async function POST(req: NextRequest) {
  try {
    const body = (await req.json()) as PublishChainRequest;
    const poster = PosterInputSchema.parse(body.poster);
    const autoFixIfQaFail = body.auto_fix_if_qa_fail ?? true;

    const qaResult = new PosterQAAutoCheck().check(poster);

    if (!qaResult.pass_qa) {
      const fixPlan = autoFixIfQaFail ? new AutoFixPosterAI().fix(poster) : null;
      return NextResponse.json({
        ok: false,
        stage: "poster_qa",
        publish_allowed: false,
        qa: qaResult,
        fix: fixPlan,
        reason: "Poster failed QA hardlock",
      });
    }

    const publishPayload = PosterPublishRequestSchema.parse({
      poster_id: poster.poster_id,
      industry: poster.industry,
      brand_name: poster.brand_name,
      headline: poster.headline || "",
      cta: poster.slogan_or_cta || "",
      value_icons: poster.value_icons,
      visual_concept: poster.visual_description || poster.product_focus || "",
      style: poster.metadata || {},
      metadata: poster.metadata || {},
    });

    const dnaResult = new WinnerDNARecallGate().evaluate(publishPayload);

    if (!dnaResult.pass_gate) {
      return NextResponse.json({
        ok: false,
        stage: "winner_dna_gate",
        publish_allowed: false,
        qa: qaResult,
        dna_gate: dnaResult,
        reason: "Winner DNA gate blocked publish",
      });
    }

    const metrics = body.metrics || {};
    const learningEvent = AdPerformanceEventSchema.parse({
      campaign_id: body.campaign_id || `campaign_${poster.poster_id}`,
      variant_id: body.variant_id || poster.poster_id,
      dna: {
        industry: poster.industry,
        hook: poster.headline || "",
        visual_concept: poster.visual_description || poster.product_focus || "",
        cta: poster.slogan_or_cta || "",
        format: "9:16",
        prompt: poster.visual_description,
      },
      impressions: metrics.impressions ?? 1000,
      clicks: metrics.clicks ?? 35,
      leads: metrics.leads ?? 4,
      sales: metrics.sales ?? 1,
      spend: metrics.spend ?? 300000,
      revenue: metrics.revenue ?? 900000,
      predicted_score: metrics.predicted_score ?? qaResult.score,
      qa_passed: true,
      metadata: {
        source: "publish-chain-orchestration",
      },
    });

    const selfLearningDecision = await new WinnerDNALearner().learnEvent(learningEvent);

    const publishAllowed = selfLearningDecision.action !== "block";

    return NextResponse.json({
      ok: publishAllowed,
      stage: "done",
      publish_allowed: publishAllowed,
      qa: qaResult,
      dna_gate: dnaResult,
      self_learning: selfLearningDecision,
      final_action: selfLearningDecision.action,
    });
  } catch (error) {
    if (error instanceof Error) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
