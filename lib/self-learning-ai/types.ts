import { z } from "zod";

export const CreativeDNASchema = z.object({
  industry: z.string(),
  hook: z.string(),
  visual_concept: z.string(),
  cta: z.string(),
  format: z.string().default("9:16"),
  provider: z.string().optional(),
  character: z.record(z.string(), z.any()).default({}),
  style: z.record(z.string(), z.any()).default({}),
  motion: z.record(z.string(), z.any()).default({}),
  prompt: z.string().optional(),
  negative_prompt: z.string().optional(),
});

export type CreativeDNA = z.infer<typeof CreativeDNASchema>;

export const AdPerformanceEventSchema = z.object({
  campaign_id: z.string(),
  variant_id: z.string(),
  dna: CreativeDNASchema,
  impressions: z.number().default(0),
  clicks: z.number().default(0),
  leads: z.number().default(0),
  sales: z.number().default(0),
  spend: z.number().default(0),
  revenue: z.number().default(0),
  predicted_score: z.number().default(0),
  qa_passed: z.boolean().default(true),
  metadata: z.record(z.string(), z.any()).default({}),
});

export type AdPerformanceEvent = z.infer<typeof AdPerformanceEventSchema>;

export const LearningDecisionSchema = z.object({
  campaign_id: z.string(),
  variant_id: z.string(),
  ctr: z.number(),
  lead_rate: z.number(),
  sale_rate: z.number(),
  roas: z.number(),
  score: z.number(),
  action: z.enum(["scale", "iterate", "kill", "block"]),
  reason: z.string(),
  learned: z.boolean(),
  next_actions: z.array(z.string()),
});

export type LearningDecision = z.infer<typeof LearningDecisionSchema>;

export const WinnerDNARecordSchema = z.object({
  dna_id: z.string(),
  campaign_id: z.string(),
  variant_id: z.string(),
  dna: CreativeDNASchema,
  performance: z.record(z.string(), z.number()),
  score: z.number(),
  created_at: z.number(),
  clone_count: z.number().default(0),
});

export type WinnerDNARecord = z.infer<typeof WinnerDNARecordSchema>;

export const CloneRequestSchema = z.object({
  dna_id: z.string(),
  count: z.number().default(3),
  variation_mode: z.enum(["hook", "cta", "visual", "mixed"]).default("mixed"),
});

export type CloneRequest = z.infer<typeof CloneRequestSchema>;

export const CloneResultSchema = z.object({
  dna_id: z.string(),
  clones: z.array(CreativeDNASchema),
});

export type CloneResult = z.infer<typeof CloneResultSchema>;

export const WeightModelSchema = z.object({
  version: z.string().default("v1"),
  weights: z.record(z.string(), z.number()),
  thresholds: z.record(z.string(), z.number()),
  sample_count: z.number().default(0),
});

export type WeightModel = z.infer<typeof WeightModelSchema>;
