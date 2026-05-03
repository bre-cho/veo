export type V6ProGoal = "authority" | "viral" | "conversion" | "brand";

export type V6ProInput = {
  product_type?: string;
  product_info?: string;
  description?: string;
  goal?: string;
  objective?: string;
  brand?: string;
  brand_name?: string;
  ratio?: string;
  style?: string;
  emotion?: string;
  font?: string;
  platform?: string;
  cta?: string;
};

export type V6ProBrain = {
  industry: string;
  goal: string;
  style: string;
  emotion: string;
  font: string;
  ratio: string;
  platform: string;
};

export type V6ProVariant = {
  type: "authority" | "viral" | "conversion";
  hook: string;
  offer: string;
  cta: string;
  prompt: string;
};

export type V6ProScore = {
  attention: number;
  trust: number;
  conversion: number;
  visual: number;
  total: number;
};

export type V6ProScoredVariant = V6ProVariant & {
  score: V6ProScore;
};

const INDUSTRY_KEYWORDS: Record<string, string[]> = {
  fashion: ["fashion", "thoi trang", "thời trang", "vay", "váy", "ao", "áo", "lookbook", "streetwear"],
  gift: ["gift", "qua", "quà", "qua tang", "quà tặng", "tri an", "tri ân", "doanh nghiep", "doanh nghiệp"],
  spa: ["spa", "skincare", "my pham", "mỹ phẩm", "mun", "mụn", "beauty", "botox", "filler"],
  food: ["food", "do an", "đồ ăn", "nuoc ep", "nước ép", "snack", "sua chua", "sữa chua"],
  tech: ["tech", "cong nghe", "công nghệ", "laptop", "smartphone", "saas", "ai"]
};

const HOOKS: Record<string, Record<"authority" | "viral" | "conversion", string>> = {
  fashion: {
    authority: "Một outfit - nâng tầm khí chất",
    viral: "Phong cách khiến bạn được chú ý",
    conversion: "BST mới dành cho người muốn nổi bật hôm nay"
  },
  gift: {
    authority: "Tri ân khách hàng - gắn kết lâu dài",
    viral: "Một món quà - vạn lời cảm ơn",
    conversion: "Đặt giftset doanh nghiệp cao cấp ngay hôm nay"
  },
  spa: {
    authority: "Nâng tầm nhan sắc với chuyên gia thẩm mỹ",
    viral: "Bạn đang mất tự tin vì làn da xuống cấp?",
    conversion: "Đặt lịch tư vấn miễn phí hôm nay"
  },
  food: {
    authority: "Vị ngon được nâng tầm thành trải nghiệm",
    viral: "Vụ nổ vị giác trong từng khoảnh khắc",
    conversion: "Thử ngay hôm nay - ngon khó cưỡng"
  },
  tech: {
    authority: "Công nghệ giúp thương hiệu vận hành thông minh hơn",
    viral: "Tương lai đang nằm trong tay bạn",
    conversion: "Dùng thử giải pháp ngay hôm nay"
  },
  general: {
    authority: "Thương hiệu chuyên nghiệp bắt đầu từ hình ảnh",
    viral: "Visual khiến khách hàng phải dừng lại",
    conversion: "Tạo quảng cáo bán hàng ngay hôm nay"
  }
};

const OFFER = {
  authority: "Premium branding visual",
  viral: "High attention creative",
  conversion: "CTA ro rang - toi uu chuyen doi"
};

function includesAny(text: string, words: string[]) {
  const lower = String(text || "").toLowerCase();
  return words.some((word) => lower.includes(word));
}

export function detectIndustry(input: V6ProInput = {}) {
  const text = JSON.stringify(input).toLowerCase();

  for (const [industry, keywords] of Object.entries(INDUSTRY_KEYWORDS)) {
    if (keywords.some((keyword) => text.includes(keyword))) {
      return industry;
    }
  }

  return "general";
}

export function buildBrainDecision(input: V6ProInput, industry: string): V6ProBrain {
  const goal = input.goal || input.objective || "conversion";

  const styleByIndustry: Record<string, string> = {
    fashion: "editorial fashion, campaign lookbook",
    gift: "premium corporate gift, luxury flatlay",
    spa: "luxury beauty clinic, cinematic editorial",
    food: "high-impact product photography, appetite visual",
    tech: "futuristic product CGI, clean UI lighting",
    general: "commercial advertising poster"
  };

  const fontByIndustry: Record<string, string> = {
    fashion: "Playfair Display / Raleway / SVN-Gilroy",
    gift: "Playfair Display / Be Vietnam Pro / Dancing Script",
    spa: "Raleway / SVN-Gilroy / Be Vietnam Pro",
    food: "Montserrat / League Spartan / Be Vietnam Pro",
    tech: "Inter / Montserrat / Be Vietnam Pro",
    general: "Be Vietnam Pro / Montserrat"
  };

  const emotionByGoal: Record<string, string> = {
    authority: "trust, premium, expert positioning",
    viral: "attention, surprise, high contrast",
    conversion: "clear desire, urgency, direct CTA",
    brand: "recognition, consistency, premium recall"
  };

  return {
    industry,
    goal,
    style: input.style || styleByIndustry[industry] || styleByIndustry.general,
    emotion: input.emotion || emotionByGoal[goal] || emotionByGoal.conversion,
    font: input.font || fontByIndustry[industry] || fontByIndustry.general,
    ratio: input.ratio || "4:5",
    platform: input.platform || "Meta/TikTok draft"
  };
}

export function generateIndustryAds(input: V6ProInput, brain: V6ProBrain) {
  const product = input.product_info || input.product_type || input.description || "main product";
  const brand = input.brand || input.brand_name || "brand";
  const industryHooks = HOOKS[brain.industry] || HOOKS.general;

  const basePrompt = [
    brain.style,
    `main subject: ${product}`,
    `brand: ${brand}`,
    `emotion: ${brain.emotion}`,
    "composition: clean commercial layout, strong focal point, clear product visibility",
    "lighting: cinematic softbox, premium highlights, controlled shadows",
    `typography: Vietnamese Unicode text, font suggestion: ${brain.font}`,
    `ratio: ${brain.ratio}`,
    "high resolution, advertising-ready, no distorted text, no cropped product"
  ].join(", ");

  return {
    authority: {
      type: "authority",
      hook: industryHooks.authority,
      offer: OFFER.authority,
      cta: "Xem bo suu tap / Tim hieu them",
      prompt: `${basePrompt}, authority version, minimal premium layout, expert trust, refined color palette`
    },
    viral: {
      type: "viral",
      hook: industryHooks.viral,
      offer: OFFER.viral,
      cta: "Kham pha ngay",
      prompt: `${basePrompt}, viral version, bold visual contrast, dynamic motion, strong attention hook, feed-stopping composition`
    },
    conversion: {
      type: "conversion",
      hook: industryHooks.conversion,
      offer: OFFER.conversion,
      cta: input.cta || "Inbox / Quet QR nhan tu van mien phi",
      prompt: `${basePrompt}, conversion version, clear CTA area, offer block, proof block, product benefit visible, direct response ad layout`
    }
  } satisfies Record<"authority" | "viral" | "conversion", V6ProVariant>;
}

export function scoreOne(variant: V6ProVariant, brain: V6ProBrain): V6ProScore {
  const prompt = variant.prompt || "";
  const hook = variant.hook || "";
  const cta = variant.cta || "";

  const attention =
    45 +
    (includesAny(prompt, ["dynamic", "bold", "motion", "contrast"]) ? 20 : 0) +
    (variant.type === "viral" ? 15 : 0);

  const trust =
    45 +
    (includesAny(prompt, ["premium", "luxury", "expert", "refined"]) ? 25 : 0) +
    (variant.type === "authority" ? 15 : 0);

  const conversion =
    45 +
    (hook.length > 18 ? 10 : 0) +
    (cta.length > 8 ? 15 : 0) +
    (includesAny(prompt, ["cta", "offer", "proof", "benefit"]) ? 20 : 0) +
    (variant.type === "conversion" ? 15 : 0);

  const visual =
    50 +
    (includesAny(prompt, ["cinematic", "softbox", "high resolution", "commercial"]) ? 20 : 0) +
    (brain.ratio ? 10 : 0);

  const total = Math.round(attention * 0.28 + trust * 0.22 + conversion * 0.35 + visual * 0.15);

  return {
    attention: Math.min(attention, 100),
    trust: Math.min(trust, 100),
    conversion: Math.min(conversion, 100),
    visual: Math.min(visual, 100),
    total: Math.min(total, 100)
  };
}

export function scoreVariants(
  variants: Record<"authority" | "viral" | "conversion", V6ProVariant>,
  brain: V6ProBrain
) {
  return Object.fromEntries(
    Object.entries(variants).map(([key, variant]) => [
      key,
      {
        ...variant,
        score: scoreOne(variant, brain)
      }
    ])
  ) as Record<"authority" | "viral" | "conversion", V6ProScoredVariant>;
}

export function pickWinner(
  scoredVariants: Record<"authority" | "viral" | "conversion", V6ProScoredVariant>
) {
  return Object.values(scoredVariants).sort((left, right) => right.score.total - left.score.total)[0] || null;
}

export function buildNextOptimizationHints(winner: V6ProScoredVariant | null, brain: V6ProBrain) {
  if (!winner) {
    return [];
  }

  const hints: string[] = [];

  if (winner.score.attention < 75) {
    hints.push("Tang visual contrast, motion, bold object scale de cai thien attention.");
  }
  if (winner.score.trust < 75) {
    hints.push("Them proof block, expert cue, premium typography de tang trust.");
  }
  if (winner.score.conversion < 80) {
    hints.push("Lam CTA ro hon, them offer/urgency/proof de tang conversion.");
  }

  hints.push(`Giu huong winner: ${winner.type}, style: ${brain.style}.`);
  return hints;
}

export async function runAdsFactoryV6Pro(input: V6ProInput) {
  const industry = detectIndustry(input);
  const brain = buildBrainDecision(input, industry);
  const variants = generateIndustryAds(input, brain);
  const scored_variants = scoreVariants(variants, brain);
  const winner = pickWinner(scored_variants);
  const next_hints = buildNextOptimizationHints(winner, brain);

  return {
    input,
    industry,
    brain,
    variants,
    scored_variants,
    winner,
    next_hints,
    created_at: new Date().toISOString()
  };
}