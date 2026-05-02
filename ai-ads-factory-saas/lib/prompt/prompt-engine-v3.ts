export type Goal = "CTR" | "Lead" | "Sale";
export type Platform = "TikTok" | "Facebook" | "Landing";
export type Mode = "Money" | "Viral" | "Premium";

export type DesignLock = {
  colors: {
    primary: string;
    accent: string;
    highlight?: string;
    background: string;
    surface: string;
    text: string;
  };
};

export type PromptV3Input = {
  product: string;
  industry: string;
  audience: string;
  offer?: string;
  goal: Goal;
  platform: Platform;
  mode: Mode;
};

export type AdOutputV3 = {
  id: string;
  score: number;
  concept: string;
  angle: string;
  hook: string;
  headline: string;
  cta: string;
  layout: {
    type: "left-text-right-visual" | "split-before-after" | "center-focus";
    textPosition: "left" | "top" | "center";
    ctaPosition: "bottom" | "bottom-right" | "center";
    visualFocus: "product" | "person" | "ui" | "result";
  };
  visual: {
    scene: string;
    lighting: string;
    colorMood: string;
    motionHint: string;
  };
  prompt2D: string;
  promptVideo: string;
  whyItConverts: string;
};

const hookBank = {
  pain: [
    "Bạn đang đốt tiền ads mà không có khách?",
    "Bạn đang mất khách vì visual quá yếu?",
    "Ads đẹp nhưng không ai click?"
  ],
  curiosity: [
    "Xem cái này trước khi bạn chạy ads",
    "Không ai nói với bạn điều này",
    "Một thay đổi nhỏ làm khách hiểu nhanh hơn"
  ],
  result: [
    "Tăng CTR chỉ với 1 thay đổi",
    "Tạo ads bán hàng trong 60 giây",
    "1 visual giúp khách hiểu sản phẩm nhanh hơn"
  ],
  fomo: [
    "Đối thủ bạn đang dùng kiểu ads này",
    "Bạn có đang bỏ lỡ khách mỗi ngày?",
    "Đừng để ads của bạn tụt lại"
  ]
};

const layouts: AdOutputV3["layout"][] = [
  { type: "left-text-right-visual", textPosition: "left", ctaPosition: "bottom-right", visualFocus: "product" },
  { type: "split-before-after", textPosition: "top", ctaPosition: "bottom", visualFocus: "result" },
  { type: "center-focus", textPosition: "center", ctaPosition: "bottom", visualFocus: "person" }
];

export function generatePromptV3(input: PromptV3Input, design: DesignLock) {
  const angles = selectAngles(input);
  const hooks = angles.flatMap((a) => hookBank[a as keyof typeof hookBank]);

  return hooks.flatMap((hook, hookIndex) =>
    layouts.map((layout, layoutIndex) => {
      const headline = makeHeadline(input);
      const cta = makeCTA(input.goal);
      const visual = makeVisual(input, layout);
      const score = scoreAd(input, hook, layout);

      return {
        id: `${input.platform}-${input.goal}-${hookIndex}-${layoutIndex}`,
        score,
        concept: makeConcept(layout),
        angle: getAngleFromHook(hook),
        hook,
        headline,
        cta,
        layout,
        visual,
        prompt2D: build2DPrompt(input, design, hook, headline, cta, layout, visual),
        promptVideo: buildVideoPrompt(input, design, hook, headline, cta, layout, visual),
        whyItConverts: `Hook tạo ${getAngleFromHook(hook)}, layout ${layout.type}, CTA bám mục tiêu ${input.goal}.`
      };
    })
  ).sort((a, b) => b.score - a.score);
}

function selectAngles(input: PromptV3Input) {
  if (input.mode === "Money") return ["pain", "result", "fomo"];
  if (input.mode === "Viral") return ["curiosity", "fomo", "pain"];
  return ["result", "curiosity"];
}

function makeHeadline(input: PromptV3Input) {
  if (input.goal === "Lead") return `Nhận demo cho ${input.product}`;
  if (input.goal === "Sale") return `Ưu đãi cho ${input.product}`;
  return `${input.product} trong 60 giây`;
}

function makeCTA(goal: Goal) {
  if (goal === "Lead") return "Nhận demo miễn phí";
  if (goal === "Sale") return "Mua ngay";
  return "Xem video ngay";
}

function makeConcept(layout: AdOutputV3["layout"]) {
  if (layout.type === "split-before-after") return "Before/After transformation";
  if (layout.type === "left-text-right-visual") return "Direct response ad layout";
  return "Hero focus conversion layout";
}

function makeVisual(input: PromptV3Input, layout: AdOutputV3["layout"]) {
  return {
    scene: layout.type === "split-before-after" ? "before state versus after result" : `${input.product} commercial showcase`,
    lighting: input.mode === "Premium" ? "soft premium studio lighting" : "high contrast cinematic lighting",
    colorMood: input.mode === "Viral" ? "bold energetic scroll-stopping" : "clean high contrast conversion-focused",
    motionHint: input.platform === "TikTok" ? "fast cut, motion blur, beat synced" : "static clear composition"
  };
}

function build2DPrompt(input: PromptV3Input, design: DesignLock, hook: string, headline: string, cta: string, layout: AdOutputV3["layout"], visual: AdOutputV3["visual"]) {
  return `
High-converting advertising creative for ${input.product}.
Industry: ${input.industry}.
Audience: ${input.audience}.
Goal: ${input.goal}.
Platform: ${input.platform}.
Mode: ${input.mode}.
Offer: ${input.offer || "clear commercial offer"}.

Hook: "${hook}"
Headline: "${headline}"
CTA: "${cta}"

Layout: ${layout.type}
Text position: ${layout.textPosition}
CTA position: ${layout.ctaPosition}
Visual focus: ${layout.visualFocus}

Visual scene: ${visual.scene}
Lighting: ${visual.lighting}
Color mood: ${visual.colorMood}

Brand lock:
Primary: ${design.colors.primary}
Accent: ${design.colors.accent}
Highlight: ${design.colors.highlight || design.colors.accent}
Background: ${design.colors.background}
Text: ${design.colors.text}

Rules:
One message only, maximum 3 lines of text, visible CTA, high contrast, do not break brand.
`.trim();
}

function buildVideoPrompt(input: PromptV3Input, design: DesignLock, hook: string, headline: string, cta: string, layout: AdOutputV3["layout"], visual: AdOutputV3["visual"]) {
  return `
Create a 9:16 short video ad for ${input.product}.
0-2s: Hook — "${hook}"
2-4s: Show problem / before state
4-5s: Smooth transition with ${visual.motionHint}
5-8s: Show after/result
8-12s: CTA — "${cta}"

Brand colors: ${design.colors.primary}, ${design.colors.accent}, ${design.colors.highlight || design.colors.accent}
Layout: ${layout.type}
Text readable on mobile, fast pacing, clear transformation.
`.trim();
}

function scoreAd(input: PromptV3Input, hook: string, layout: AdOutputV3["layout"]) {
  let score = 70;
  if (input.goal === "Lead" && hook.includes("đốt tiền")) score += 15;
  if (input.platform === "TikTok" && layout.type === "split-before-after") score += 15;
  if (input.mode === "Money") score += 10;
  if (layout.visualFocus === "result") score += 8;
  return score;
}

function getAngleFromHook(hook: string) {
  if (hook.includes("đốt tiền") || hook.includes("mất khách")) return "pain";
  if (hook.includes("Không ai") || hook.includes("Xem cái này")) return "curiosity";
  if (hook.includes("Tăng") || hook.includes("60 giây")) return "result";
  return "fomo";
}
