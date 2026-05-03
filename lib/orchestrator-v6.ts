import {
  detectSellingMechanism,
  generateHook,
  generateCTA,
  decideLayout,
  decideVisual,
  buildPosterPrompts
} from "./prompt-v6/engine";

import { generateFunnel } from "./funnel/engine";
import { generateBotSalesFlow } from "./bot/sales-flow";
import { generateAdsPlan } from "./ads/launch-engine";

export function runV6System(input: any) {
  const mechanism = detectSellingMechanism(input);
  const hook = generateHook(mechanism);
  const cta = generateCTA(input.goal);
  const layout = decideLayout(input, mechanism);
  const visual = decideVisual(mechanism);

  const posterPrompts = buildPosterPrompts(input, {
    mechanism,
    hook,
    cta,
    layout,
    visual
  });

  return {
    strategy: `Hệ thống phải khiến người xem ${input.goal === "sale" ? "muốn mua" : "muốn tìm hiểu"} trong 3 giây.`,
    mechanism,
    hook,
    cta,
    layout,
    visual,
    posterPrompts,
    funnel: generateFunnel(input),
    botFlow: generateBotSalesFlow(input),
    adsPlan: generateAdsPlan(input),
    kpiRules: {
      ctrLow: "Đổi hook / visual hook",
      cplHigh: "Đổi CTA / offer",
      roasHigh: "Scale winner"
    }
  };
}
