import { z } from "zod";

export const PosterInputSchema = z.object({
  poster_id: z.string().default("poster_auto"),
  industry: z.string().default("custom"),
  brand_name: z.string().optional(),
  headline: z.string().optional(),
  slogan_or_cta: z.string().optional(),
  value_icons: z.array(z.string()).default([]),
  product_focus: z.string().optional(),
  colors: z.array(z.string()).default([]),
  text_blocks: z.array(z.string()).default([]),
  visual_description: z.string().default(""),
  image_path: z.string().optional(),
  metadata: z.record(z.string(), z.any()).default({}),
});

export type PosterInput = z.infer<typeof PosterInputSchema>;

export const QAIssueSchema = z.object({
  rule_id: z.string(),
  severity: z.enum(["blocker", "major", "minor"]),
  message: z.string(),
  fix: z.string(),
});

export type QAIssue = z.infer<typeof QAIssueSchema>;

export const QACheckResultSchema = z.object({
  poster_id: z.string(),
  pass_qa: z.boolean(),
  score: z.number(),
  issues: z.array(QAIssueSchema),
  checklist: z.record(z.string(), z.boolean()),
  decision: z.enum(["publish", "fix_required", "reject"]),
});

export type QACheckResult = z.infer<typeof QACheckResultSchema>;

export const PosterFixPlanSchema = z.object({
  poster_id: z.string(),
  rewritten_headline: z.string(),
  rewritten_cta: z.string(),
  required_icons: z.array(z.string()),
  layout_fix: z.array(z.string()),
  color_lighting_fix: z.array(z.string()),
  prompt_patch: z.string(),
  negative_prompt_patch: z.string(),
});

export type PosterFixPlan = z.infer<typeof PosterFixPlanSchema>;

export const CTRMetricEventSchema = z.object({
  poster_id: z.string(),
  impressions: z.number().default(0),
  clicks: z.number().default(0),
  leads: z.number().default(0),
  sales: z.number().default(0),
  spend: z.number().default(0),
  revenue: z.number().default(0),
});

export type CTRMetricEvent = z.infer<typeof CTRMetricEventSchema>;

export const CTROptimizationResultSchema = z.object({
  poster_id: z.string(),
  ctr: z.number(),
  lead_rate: z.number(),
  roas: z.number(),
  optimizer_score: z.number(),
  action: z.enum(["scale", "iterate", "kill"]),
  recommended_fix: z.array(z.string()),
});

export type CTROptimizationResult = z.infer<
  typeof CTROptimizationResultSchema
>;

export const PosterToVideoRequestSchema = z.object({
  poster: PosterInputSchema,
  duration_seconds: z.number().default(10),
  provider: z.string().default("mock"),
  aspect_ratio: z.string().default("9:16"),
  character: z.record(z.string(), z.any()).default({}),
  style: z.record(z.string(), z.any()).default({}),
  motion: z.record(z.string(), z.any()).default({}),
});

export type PosterToVideoRequest = z.infer<typeof PosterToVideoRequestSchema>;

export const PosterToVideoPlanSchema = z.object({
  poster_id: z.string(),
  scenes: z.array(z.record(z.string(), z.any())),
  render_payload: z.record(z.string(), z.any()),
  provider: z.string(),
});

export type PosterToVideoPlan = z.infer<typeof PosterToVideoPlanSchema>;
