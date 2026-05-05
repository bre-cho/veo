import { z } from "zod";

export const PresetTemplateSchema = z.object({
  template_id: z.string(),
  name: z.string(),
  engine: z.string(),
  industry: z.string(),
  category: z.string(),
  format: z.string(),
  qa_hardlock: z.record(z.string(), z.any()).default({}),
  recommended_text: z.record(z.string(), z.any()).default({}),
  prompt: z.string(),
  negative_prompt: z.string().default(""),
  ctr_notes: z.record(z.string(), z.any()).default({}),
});

export type PresetTemplate = z.infer<typeof PresetTemplateSchema>;

export const TemplateRenderRequestSchema = z.object({
  template_id: z.string(),
  brand_name: z.string().optional(),
  headline: z.string().optional(),
  cta: z.string().optional(),
  icons: z.array(z.string()).optional(),
  product_name: z.string().optional(),
  extra_notes: z.string().optional(),
});

export type TemplateRenderRequest = z.infer<typeof TemplateRenderRequestSchema>;
