import yaml from "js-yaml";
import { DesignSystem, DesignSystemSchema } from "./schema";

export function parseDesignMd(content: string): DesignSystem {
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) throw new Error("DESIGN.md thiếu YAML frontmatter.");
  const raw = yaml.load(match[1]);
  return DesignSystemSchema.parse(raw);
}
