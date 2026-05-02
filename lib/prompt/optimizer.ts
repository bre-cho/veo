import { DesignSystem } from "@/lib/design/schema";

type Goal = "CTR" | "Lead" | "Sale";
type Platform = "TikTok" | "Facebook" | "Landing";
type Mode = "Money" | "Viral" | "Premium";

export type PromptInput = {
  product: string;
  audience: string;
  offer?: string;
  industry: string;
  goal: Goal;
  platform: Platform;
  mode: Mode;
};

const hooks = {
  pain: [
    "Bạn đang đốt tiền ads mà không có khách?",
    "Bạn đang mất bao nhiêu khách vì điều này?",
    "Tại sao bạn chưa bán được hàng?"
  ],
  curiosity: [
    "Xem cái này trước khi bạn chạy ads",
    "Không ai nói với bạn điều này",
    "Điều này thay đổi cách bán hàng"
  ],
  result: [
    "Tăng CTR chỉ với 1 thay đổi",
    "Khách hiểu sản phẩm nhanh hơn",
    "1 visual giúp bán hàng tốt hơn"
  ],
  fomo: [
    "Đối thủ bạn đang dùng cái này",
    "Bạn đang tụt lại phía sau",
    "Bạn có đang bỏ lỡ cơ hội này?"
  ]
};

const visualMap = {
  TikTok: [
    "fast before-after transformation",
    "AI demo workflow from text to final ad",
    "human reaction with strong emotion"
  ],
  Facebook: [
    "left hook text, right product visual",
    "clean product ad with offer badge",
    "testimonial proof block with CTA"
  ],
  Landing: [
    "hero section with UI mockup",
    "problem-solution section",
    "comparison before-after section"
  ]
};

export function generateOptimizedPrompts(input: PromptInput, ds: DesignSystem) {
  const selectedHooks = selectHooks(input);
  const visuals = visualMap[input.platform];

  return selectedHooks.flatMap((hook) =>
    visuals.map((visual) => {
      const cta = getCta(input.goal);
      const score = scorePrompt(input, hook, visual);

      return {
        score,
        hook,
        visual,
        cta,
        prompt: `
High-converting ${input.platform} ad creative.

Product: ${input.product}
Industry: ${input.industry}
Audience: ${input.audience}
Goal: ${input.goal}
Offer: ${input.offer || "clear offer"}

Hook: "${hook}"
CTA: "${cta}"
Visual: ${visual}

DESIGN.md brand lock:
- Primary: ${ds.colors.primary}
- Accent: ${ds.colors.accent}
- Highlight: ${ds.colors.highlight || ds.colors.accent}
- Background: ${ds.colors.background}
- Surface: ${ds.colors.surface}
- Text: ${ds.colors.text}

Rules:
- 1 message only
- maximum 3 text lines
- CTA must be visible
- product or face must be main focus
- strong contrast
- conversion-focused layout
- do not break brand system
`.trim()
      };
    })
  ).sort((a, b) => b.score - a.score);
}

function selectHooks(input: PromptInput) {
  if (input.mode === "Viral") return [...hooks.curiosity, ...hooks.fomo];
  if (input.mode === "Premium") return [...hooks.result, ...hooks.curiosity];
  if (input.goal === "Lead") return [...hooks.pain, ...hooks.result];
  if (input.goal === "Sale") return [...hooks.result, ...hooks.fomo];
  return [...hooks.curiosity, ...hooks.result];
}

function getCta(goal: Goal) {
  if (goal === "Lead") return "Nhận demo miễn phí";
  if (goal === "Sale") return "Mua ngay";
  return "Xem video ngay";
}

function scorePrompt(input: PromptInput, hook: string, visual: string) {
  let score = 70;
  if (input.goal === "Lead" && hook.includes("đốt tiền")) score += 15;
  if (input.platform === "TikTok" && visual.includes("fast")) score += 12;
  if (input.mode === "Money") score += 8;
  return score;
}
