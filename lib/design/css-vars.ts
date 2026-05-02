import { DesignSystem } from "./schema";

export function designToCssVars(ds: DesignSystem) {
  return {
    "--color-primary": ds.colors.primary,
    "--color-secondary": ds.colors.secondary || ds.colors.primary,
    "--color-accent": ds.colors.accent,
    "--color-highlight": ds.colors.highlight || ds.colors.accent,
    "--color-background": ds.colors.background,
    "--color-surface": ds.colors.surface,
    "--color-text": ds.colors.text,
    "--radius-md": ds.rounded?.md || "8px",
    "--radius-lg": ds.rounded?.lg || "16px"
  } as React.CSSProperties;
}
