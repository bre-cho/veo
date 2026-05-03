import yaml from "js-yaml";
import { z } from "zod";

export const DesignMdSchema = z.object({
  version: z.union([z.string(), z.number()]).optional(),
  name: z.string(),
  description: z.string().optional(),
  colors: z.record(z.string(), z.string()),
  typography: z.record(z.string(), z.any()).optional(),
  layout: z.record(z.string(), z.any()).optional(),
  visual: z.record(z.string(), z.any()).optional(),
  rules: z.record(z.string(), z.any()).optional()
});

export function parseDesignMd(content: string) {
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) throw new Error("Missing YAML frontmatter");

  const raw = yaml.load(match[1]);
  return DesignMdSchema.parse(raw);
}

export function buildDesignLock(ds: any) {
  return {
    name: ds.name,
    colors: ds.colors,
    typography: ds.typography || {},
    layout: ds.layout || {},
    rules: ds.rules || {}
  };
}
