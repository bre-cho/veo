import {
  detectSellingMechanism,
  generateHook,
  generateCTA,
  decideVisual
} from "./prompt-v6/engine";

export function runSystem(input: any) {
  const normalized = {
    text: String(input?.text || ""),
    product: input?.product,
    industry: input?.industry,
    audience: input?.audience,
    goal: input?.goal || "lead",
    hasCollection: Boolean(input?.hasCollection),
    hasPackaging: Boolean(input?.hasPackaging)
  };

  const mechanism = detectSellingMechanism(normalized);

  return {
    mechanism,
    hook: generateHook(mechanism),
    cta: generateCTA(normalized.goal),
    visual: decideVisual(mechanism),
    funnel: {
      landing: "Landing co ban",
      followup: ["Ban can demo khong?", "Minh ho tro ban"]
    }
  };
}
