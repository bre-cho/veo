import { z } from "zod";

export const PosterPublishRequestSchema = z.object({
  poster_id: z.string(),
  industry: z.string(),
  brand_name: z.string().optional(),
  headline: z.string(),
  cta: z.string(),
  value_icons: z.array(z.string()).default([]),
  visual_concept: z.string().default(""),
  style: z.record(z.string(), z.any()).default({}),
  metadata: z.record(z.string(), z.any()).default({}),
});

export type PosterPublishRequest = z.infer<
  typeof PosterPublishRequestSchema
>;

export const WinnerDNAMatchSchema = z.object({
  dna_id: z.string(),
  industry: z.string(),
  hook: z.string(),
  visual_concept: z.string(),
  cta: z.string(),
  score: z.number(),
  similarity: z.number(),
  reason: z.string(),
});

export type WinnerDNAMatch = z.infer<typeof WinnerDNAMatchSchema>;

export const WinnerDNAGateResultSchema = z.object({
  poster_id: z.string(),
  industry: z.string(),
  pass_gate: z.boolean(),
  decision: z.enum(["publish", "fix_required", "reject"]),
  best_match: WinnerDNAMatchSchema.optional(),
  required_fixes: z.array(z.string()),
  recalled_winners_count: z.number(),
  rule: z.string().default("NO DNA MATCH → BLOCK"),
});

export type WinnerDNAGateResult = z.infer<typeof WinnerDNAGateResultSchema>;
