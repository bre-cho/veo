import { z } from "zod";

export const IndustryDetectRequestSchema = z.object({
  text: z.string(),
  product_name: z.string().optional(),
  image_description: z.string().optional(),
  metadata: z.record(z.string(), z.any()).default({}),
});

export type IndustryDetectRequest = z.infer<typeof IndustryDetectRequestSchema>;

export const IndustryDetectResultSchema = z.object({
  industry: z.string(),
  parent_category: z.string(),
  confidence: z.number(),
  matched_keywords: z.array(z.string()),
  recommended_engine: z.string(),
  recommended_visual_law: z.record(z.string(), z.any()),
});

export type IndustryDetectResult = z.infer<typeof IndustryDetectResultSchema>;

export const WinnerLearningInputSchema = z.object({
  campaign_id: z.string(),
  variant_id: z.string(),
  industry: z.string(),
  hook: z.string(),
  visual_concept: z.string(),
  cta: z.string(),
  metrics: z.record(z.string(), z.number()),
  creative_dna: z.record(z.string(), z.any()).default({}),
});

export type WinnerLearningInput = z.infer<typeof WinnerLearningInputSchema>;

export const WinnerLearningResultSchema = z.object({
  saved: z.boolean(),
  winner_score: z.number(),
  learned_dna: z.record(z.string(), z.any()),
  clone_recommendations: z.array(z.string()),
});

export type WinnerLearningResult = z.infer<typeof WinnerLearningResultSchema>;

export const FunnelGenerateRequestSchema = z.object({
  campaign_id: z.string(),
  industry: z.string(),
  product_name: z.string(),
  audience: z.string(),
  offer: z.string().optional(),
  pain_point: z.string(),
  desired_outcome: z.string(),
  proof: z.string().optional(),
  cta: z.string().default("Nhận tư vấn miễn phí"),
});

export type FunnelGenerateRequest = z.infer<typeof FunnelGenerateRequestSchema>;

export const FunnelGenerateResultSchema = z.object({
  campaign_id: z.string(),
  ad_angle: z.record(z.string(), z.any()),
  landing_page: z.record(z.string(), z.any()),
  crm_flow: z.array(z.record(z.string(), z.any())),
  close_script: z.array(z.string()),
  tracking_events: z.array(z.string()),
});

export type FunnelGenerateResult = z.infer<typeof FunnelGenerateResultSchema>;

export const CTRTrackingEventSchema = z.object({
  campaign_id: z.string(),
  variant_id: z.string(),
  industry: z.string().default("custom"),
  impressions: z.number().default(0),
  clicks: z.number().default(0),
  leads: z.number().default(0),
  sales: z.number().default(0),
  spend: z.number().default(0),
  revenue: z.number().default(0),
});

export type CTRTrackingEvent = z.infer<typeof CTRTrackingEventSchema>;

export const CTRTrackingResultSchema = z.object({
  campaign_id: z.string(),
  variant_id: z.string(),
  ctr: z.number(),
  lead_rate: z.number(),
  sale_rate: z.number(),
  cpl: z.number().nullable(),
  cpa: z.number().nullable(),
  roas: z.number(),
  decision: z.enum(["scale", "iterate", "kill"]),
  reason: z.string(),
  next_action: z.array(z.string()),
});

export type CTRTrackingResult = z.infer<typeof CTRTrackingResultSchema>;
