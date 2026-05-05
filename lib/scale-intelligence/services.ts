import path from "path";
import fs from "fs/promises";
import {
  IndustryDetectRequest,
  IndustryDetectResult,
  WinnerLearningInput,
  WinnerLearningResult,
  FunnelGenerateRequest,
  FunnelGenerateResult,
  CTRTrackingEvent,
  CTRTrackingResult,
} from "./types";
import { INDUSTRY_KEYWORDS } from "./industry-keywords";

const PARENT: Record<string, string> = {
  skincare: "beauty",
  makeup: "beauty",
  spa: "beauty",
  hair_salon: "beauty",
  nail: "beauty",
  clinic: "beauty",
  perfume: "beauty",
  organic_beauty: "beauty",
  anti_aging: "beauty",
  acne_treatment: "beauty",
  fast_food: "fnb",
  cafe: "fnb",
  milk_tea: "fnb",
  fine_dining: "fnb",
  street_food: "fnb",
  healthy_food: "fnb",
  bakery: "fnb",
  bbq: "fnb",
  seafood: "fnb",
  dessert: "fnb",
  streetwear: "fashion",
  luxury_fashion: "fashion",
  local_brand: "fashion",
  sportswear: "fashion",
  kids_fashion: "fashion",
  office_wear: "fashion",
  vintage: "fashion",
  minimal: "fashion",
  apartment: "real_estate",
  townhouse: "real_estate",
  villa: "real_estate",
  land: "real_estate",
  rental: "real_estate",
  online_course: "digital",
  coaching: "digital",
  marketing_service: "digital",
  saas: "digital",
  app: "digital",
  freelance: "digital",
  mmo: "digital",
  car: "other",
  motorbike: "other",
  gym: "other",
  yoga: "other",
  travel: "other",
  wedding: "other",
  event: "other",
  interior: "other",
  education: "other",
  finance: "other",
};

const VISUAL: Record<string, Record<string, unknown>> = {
  beauty: {
    engine: "transformation",
    focus: "face/skin/product",
    colors: ["gold", "beige", "white"],
    icons: ["Dưỡng trắng", "Cấp ẩm", "Bảo vệ"],
  },
  fnb: {
    engine: "craving",
    focus: "macro texture/product",
    colors: ["red", "green", "yellow"],
    icons: ["Tươi ngon", "Ưu đãi", "Giao nhanh"],
  },
  fashion: {
    engine: "identity",
    focus: "model/outfit",
    colors: ["black", "beige", "white"],
    icons: ["Tôn dáng", "Chất liệu", "Dễ phối"],
  },
  real_estate: {
    engine: "trust",
    focus: "space/view/location",
    colors: ["blue", "gold", "white"],
    icons: ["Vị trí", "Pháp lý", "Tiện ích"],
  },
  digital: {
    engine: "solution",
    focus: "UI/result/demo",
    colors: ["dark", "blue", "neon"],
    icons: ["Nhanh", "Tự động", "Tăng trưởng"],
  },
  other: {
    engine: "lifestyle",
    focus: "aspiration/result",
    colors: ["premium", "contrast"],
    icons: ["Giá trị", "Uy tín", "Hiệu quả"],
  },
};

const STORE = path.join(process.cwd(), "data", "winner-learning-store.json");

export class AutoIndustryDetector {
  detect(req: IndustryDetectRequest): IndustryDetectResult {
    const text = [req.text || "", req.product_name || "", req.image_description || ""]
      .join(" ")
      .toLowerCase();

    let bestIndustry = "custom";
    let bestMatches: string[] = [];

    for (const [industry, keywords] of Object.entries(INDUSTRY_KEYWORDS)) {
      const matches = keywords.filter((k) => text.includes(k.toLowerCase()));
      if (matches.length > bestMatches.length) {
        bestIndustry = industry;
        bestMatches = matches;
      }
    }

    const parent = PARENT[bestIndustry] || "other";
    const confidence = Math.min(0.99, 0.35 + bestMatches.length * 0.18);
    const visual = VISUAL[parent] || VISUAL.other;

    return {
      industry: bestIndustry,
      parent_category: parent,
      confidence: Number(confidence.toFixed(2)),
      matched_keywords: bestMatches,
      recommended_engine: String(visual.engine || "lifestyle"),
      recommended_visual_law: visual,
    };
  }
}

export class WinnerLearningEngine {
  private score(metrics: Record<string, number>): number {
    const impressions = metrics.impressions || 0;
    const clicks = metrics.clicks || 0;
    const leads = metrics.leads || 0;
    const sales = metrics.sales || 0;
    const spend = metrics.spend || 0;
    const revenue = metrics.revenue || 0;

    const ctr = impressions ? clicks / impressions : 0;
    const leadRate = clicks ? leads / clicks : 0;
    const saleRate = leads ? sales / leads : 0;
    const roas = spend ? revenue / spend : 0;

    return (
      Math.min(ctr * 1000, 35) +
      Math.min(leadRate * 100, 25) +
      Math.min(saleRate * 100, 20) +
      Math.min(roas * 5, 20)
    );
  }

  async learn(input: WinnerLearningInput): Promise<WinnerLearningResult> {
    const winnerScore = Number(this.score(input.metrics).toFixed(2));
    const learnedDNA = {
      campaign_id: input.campaign_id,
      variant_id: input.variant_id,
      industry: input.industry,
      hook: input.hook,
      visual_concept: input.visual_concept,
      cta: input.cta,
      winner_score: winnerScore,
      creative_dna: input.creative_dna,
      saved_at: Date.now(),
    };

    const saved = winnerScore >= 85;
    if (saved) {
      await fs.mkdir(path.dirname(STORE), { recursive: true });

      let data: Record<string, unknown>[] = [];
      try {
        const raw = await fs.readFile(STORE, "utf-8");
        data = JSON.parse(raw);
      } catch {
        data = [];
      }

      const deduped = data.filter((x) => {
        const item = x as Record<string, unknown>;
        return !(
          item.industry === input.industry &&
          String(item.hook || "").toLowerCase().trim() ===
            input.hook.toLowerCase().trim() &&
          String(item.visual_concept || "").toLowerCase().trim() ===
            input.visual_concept.toLowerCase().trim()
        );
      });

      deduped.push(learnedDNA);
      await fs.writeFile(STORE, JSON.stringify(deduped, null, 2), "utf-8");
    }

    return {
      saved,
      winner_score: winnerScore,
      learned_dna: learnedDNA,
      clone_recommendations: [
        "Clone winner với 3 biến thể hook cùng pain.",
        "Giữ visual concept, đổi CTA sang offer mạnh hơn.",
        "Tạo 1 bản video 9:16 từ winner poster.",
        "Tạo retargeting version với social proof/testimonial.",
      ],
    };
  }
}

export class AutoFunnelGenerator {
  generate(req: FunnelGenerateRequest): FunnelGenerateResult {
    const adAngle = {
      hook: `${req.pain_point} - đây là cách để ${req.desired_outcome}`,
      promise: req.desired_outcome,
      offer: req.offer || req.cta,
      cta: req.cta,
    };

    const landingPage = {
      hero: {
        headline: adAngle.hook,
        subheadline: `Giải pháp cho ${req.audience}`,
        cta: req.cta,
      },
      problem: [req.pain_point, "Đang mất thời gian/tiền vì chưa có giải pháp đúng"],
      solution: [req.product_name, req.desired_outcome],
      proof: req.proof || "Case study / testimonial / số liệu thực tế",
      benefits: ["Nhanh hơn", "Rõ ràng hơn", "Dễ ra quyết định hơn"],
      final_cta: req.cta,
    };

    const crmFlow = [
      { step: 1, channel: "form/inbox", message: "Cảm ơn bạn, mình gửi demo/tư vấn ngay." },
      { step: 2, channel: "chat", message: "Bạn đang gặp vấn đề nào lớn nhất hiện tại?" },
      { step: 3, channel: "demo", message: "Đây là cách sản phẩm giải quyết đúng pain của bạn." },
      { step: 4, channel: "close", message: "Bạn muốn bắt đầu với gói nào hôm nay?" },
    ];

    const closeScript = [
      `Hiện tại vấn đề chính của bạn là ${req.pain_point}, đúng không?`,
      `Nếu giải quyết được, mục tiêu là ${req.desired_outcome}.`,
      `${req.product_name} giúp bạn đi từ pain tới outcome bằng quy trình rõ.`,
      `Hôm nay bạn có thể bắt đầu bằng: ${req.cta}.`,
    ];

    return {
      campaign_id: req.campaign_id,
      ad_angle: adAngle,
      landing_page: landingPage,
      crm_flow: crmFlow,
      close_script: closeScript,
      tracking_events: [
        "ad_impression",
        "ad_click",
        "landing_view",
        "lead_submit",
        "demo_booked",
        "purchase",
        "retarget_click",
      ],
    };
  }
}

export class RealCTRDataEngine {
  track(e: CTRTrackingEvent): CTRTrackingResult {
    const ctr = e.impressions ? e.clicks / e.impressions : 0;
    const leadRate = e.clicks ? e.leads / e.clicks : 0;
    const saleRate = e.leads ? e.sales / e.leads : 0;
    const cpl = e.leads ? e.spend / e.leads : null;
    const cpa = e.sales ? e.spend / e.sales : null;
    const roas = e.spend ? e.revenue / e.spend : 0;

    let decision: "scale" | "iterate" | "kill";
    let reason: string;
    let nextAction: string[];

    if (ctr >= 0.018 && leadRate >= 0.12 && roas >= 1) {
      decision = "scale";
      reason = "CTR/lead/ROAS đều đạt ngưỡng scale.";
      nextAction = [
        "Tăng ngân sách 20-30%",
        "Clone thêm 3 biến thể cùng DNA",
        "Chạy retargeting",
      ];
    } else if (ctr >= 0.008 || leadRate >= 0.08) {
      decision = "iterate";
      reason = "Có tín hiệu nhưng chưa đủ mạnh.";
      nextAction = ["Test hook mới", "Tăng proof/icon trust", "Đổi CTA rõ hơn"];
    } else {
      decision = "kill";
      reason = "Tín hiệu thấp.";
      nextAction = ["Dừng mẫu này", "Đổi concept visual", "Viết lại pain hook"];
    }

    return {
      campaign_id: e.campaign_id,
      variant_id: e.variant_id,
      ctr: Number(ctr.toFixed(4)),
      lead_rate: Number(leadRate.toFixed(4)),
      sale_rate: Number(saleRate.toFixed(4)),
      cpl: cpl === null ? null : Number(cpl.toFixed(2)),
      cpa: cpa === null ? null : Number(cpa.toFixed(2)),
      roas: Number(roas.toFixed(2)),
      decision,
      reason,
      next_action: nextAction,
    };
  }
}
