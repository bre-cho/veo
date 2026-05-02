import { z } from "zod";

export const DesignSystemSchema = z.object({
  version: z.string().optional(),
  name: z.string(),
  description: z.string().optional(),
  colors: z.object({
    primary: z.string(),
    secondary: z.string().optional(),
    accent: z.string(),
    highlight: z.string().optional(),
    background: z.string(),
    surface: z.string(),
    text: z.string()
  }),
  typography: z.record(z.string(), z.any()).optional(),
  spacing: z.record(z.string(), z.string()).optional(),
  rounded: z.record(z.string(), z.string()).optional(),
  components: z.record(z.string(), z.any()).optional(),
  conversion: z.object({
    goal: z.enum(["CTR", "Lead", "Sale"]).optional(),
    platform: z.enum(["TikTok", "Facebook", "Landing"]).optional(),
    primaryAction: z.string().optional()
  }).optional()
});

export type DesignSystem = z.infer<typeof DesignSystemSchema>;
