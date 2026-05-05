import crypto from "crypto";
import {
  AdPerformanceEvent,
  CloneRequest,
  CloneResult,
  CreativeDNA,
  LearningDecision,
  WinnerDNARecord,
} from "./types";
import { EVENTS, WINNERS, nowTs, readJson, writeJson } from "./storage";
import { SelfLearningScoreModel } from "./score-model";

const HOOK_VARIATIONS = [
  "Chỉ 1 thay đổi nhỏ - khác biệt ngay",
  "Bạn đang bỏ lỡ điều này mỗi ngày",
  "Kết quả nhìn thấy ngay từ lần đầu",
  "Đừng mua thêm nếu chưa xem mẫu này",
  "Mẫu đang được chọn nhiều nhất hôm nay",
];
const CTA_VARIATIONS = [
  "Mua ngay - ưu đãi hôm nay",
  "Inbox nhận tư vấn miễn phí",
  "Nhận demo ngay",
  "Đặt hàng hôm nay",
  "Chọn màu hot ngay",
];
const VISUAL_VARIATIONS = [
  "close-up product hero with stronger contrast",
  "before-after split composition",
  "social proof comment overlay",
  "luxury minimal layout",
  "motion splash/glow effect",
];

export class WinnerDNALearner {
  private model = new SelfLearningScoreModel();

  private dnaId(e: AdPerformanceEvent): string {
    const raw = `${e.dna.industry}|${e.dna.hook}|${e.dna.visual_concept}|${e.dna.cta}|${e.dna.format}`;
    return `dna_${crypto.createHash("sha1").update(raw).digest("hex").slice(0, 12)}`;
  }

  async learnEvent(e: AdPerformanceEvent): Promise<LearningDecision> {
    const events = await readJson<AdPerformanceEvent[]>(EVENTS, []);
    events.push(e);
    await writeJson(EVENTS, events);

    const model = await this.model.load();
    const scored = await this.model.score(e);

    if (!e.qa_passed) {
      return {
        campaign_id: e.campaign_id,
        variant_id: e.variant_id,
        ctr: Number(scored.ctr.toFixed(4)),
        lead_rate: Number(scored.leadRate.toFixed(4)),
        sale_rate: Number(scored.saleRate.toFixed(4)),
        roas: Number(scored.roas.toFixed(2)),
        score: scored.score,
        action: "block",
        reason: "QA hardlock failed, cannot run/scale.",
        learned: false,
        next_actions: ["Send to Poster Auto Fix", "Regenerate with QA rules"],
      };
    }

    if (
      scored.ctr >= model.thresholds.scale_ctr &&
      scored.score >= model.thresholds.scale_score
    ) {
      await this.saveWinner(e, scored.score, scored.ctr, scored.leadRate, scored.saleRate, scored.roas);

      return {
        campaign_id: e.campaign_id,
        variant_id: e.variant_id,
        ctr: Number(scored.ctr.toFixed(4)),
        lead_rate: Number(scored.leadRate.toFixed(4)),
        sale_rate: Number(scored.saleRate.toFixed(4)),
        roas: Number(scored.roas.toFixed(2)),
        score: scored.score,
        action: "scale",
        reason: "CTR >= 2.8% and score >= 90: AUTO SCALE.",
        learned: true,
        next_actions: [
          "Increase budget +30%",
          "Clone 3 new variants",
          "Expand audience",
          "Create video version",
        ],
      };
    }

    if (scored.ctr < model.thresholds.kill_ctr) {
      return {
        campaign_id: e.campaign_id,
        variant_id: e.variant_id,
        ctr: Number(scored.ctr.toFixed(4)),
        lead_rate: Number(scored.leadRate.toFixed(4)),
        sale_rate: Number(scored.saleRate.toFixed(4)),
        roas: Number(scored.roas.toFixed(2)),
        score: scored.score,
        action: "kill",
        reason: "CTR < 2.5%: AUTO KILL.",
        learned: false,
        next_actions: [
          "Stop ad",
          "Log failed DNA",
          "Send hook/visual to Auto Fix",
          "Do not clone this variant",
        ],
      };
    }

    return {
      campaign_id: e.campaign_id,
      variant_id: e.variant_id,
      ctr: Number(scored.ctr.toFixed(4)),
      lead_rate: Number(scored.leadRate.toFixed(4)),
      sale_rate: Number(scored.saleRate.toFixed(4)),
      roas: Number(scored.roas.toFixed(2)),
      score: scored.score,
      action: "iterate",
      reason: "CTR between 2.5% and 2.8% or score below scale threshold: ITERATE.",
      learned: false,
      next_actions: [
        "Test new hook",
        "Improve CTA",
        "Increase contrast",
        "Run 1 more controlled variant",
      ],
    };
  }

  private async saveWinner(
    e: AdPerformanceEvent,
    score: number,
    ctr: number,
    leadRate: number,
    saleRate: number,
    roas: number
  ) {
    const winners = await readJson<WinnerDNARecord[]>(WINNERS, []);
    const dnaId = this.dnaId(e);

    const record: WinnerDNARecord = {
      dna_id: dnaId,
      campaign_id: e.campaign_id,
      variant_id: e.variant_id,
      dna: e.dna,
      performance: {
        ctr,
        lead_rate: leadRate,
        sale_rate: saleRate,
        roas,
      },
      score,
      created_at: nowTs(),
      clone_count: 0,
    };

    const next = winners.filter((w) => w.dna_id !== dnaId);
    next.push(record);
    await writeJson(WINNERS, next);
  }

  async listWinners(): Promise<WinnerDNARecord[]> {
    return readJson<WinnerDNARecord[]>(WINNERS, []);
  }

  async retrain() {
    const raw = await readJson<AdPerformanceEvent[]>(EVENTS, []);
    return this.model.updateWeights(raw);
  }
}

export class WinnerDNACloner {
  async clone(req: CloneRequest): Promise<CloneResult> {
    const winners = await readJson<WinnerDNARecord[]>(WINNERS, []);
    const found = winners.find((w) => w.dna_id === req.dna_id);

    if (!found) {
      return { dna_id: req.dna_id, clones: [] };
    }

    const base = found.dna;
    const clones: CreativeDNA[] = [];

    for (let i = 0; i < req.count; i++) {
      const clone: CreativeDNA = { ...base };

      if (req.variation_mode === "hook" || req.variation_mode === "mixed") {
        clone.hook = HOOK_VARIATIONS[i % HOOK_VARIATIONS.length];
      }
      if (req.variation_mode === "cta" || req.variation_mode === "mixed") {
        clone.cta = CTA_VARIATIONS[i % CTA_VARIATIONS.length];
      }
      if (req.variation_mode === "visual" || req.variation_mode === "mixed") {
        clone.visual_concept = `${base.visual_concept} + ${VISUAL_VARIATIONS[i % VISUAL_VARIATIONS.length]}`;
      }

      clones.push(clone);
    }

    found.clone_count += req.count;
    await writeJson(WINNERS, winners);

    return {
      dna_id: req.dna_id,
      clones,
    };
  }
}

export class HeatmapClickPredictor {
  predict(payload: Record<string, unknown>) {
    const headline = String(payload.headline || "");
    const cta = String(payload.cta || "");
    const visualType = String(payload.visual_type || "product");
    const iconCount = Number(payload.icon_count || 0);
    const contrast = Number(payload.contrast_score || 0.7);

    const attention: Record<string, number> = {
      headline: 0.3,
      face: 0.2,
      product: 0.25,
      icons: 0.1,
      cta: 0.15,
    };

    if (visualType === "closeup_face") {
      attention.face += 0.12;
    }
    if (visualType === "product" || visualType === "product_closeup") {
      attention.product += 0.12;
    }
    if (headline.includes("?") || headline.includes("!") || headline.split(" ").length <= 6) {
      attention.headline += 0.08;
    }
    if (iconCount >= 3) {
      attention.icons += 0.05;
    }
    if (cta.toLowerCase().includes("ngay")) {
      attention.cta += 0.08;
    }
    if (contrast >= 0.8) {
      attention.headline += 0.04;
      attention.cta += 0.03;
    }

    const total = Object.values(attention).reduce((a, b) => a + b, 0);
    const normalized = Object.fromEntries(
      Object.entries(attention).map(([k, v]) => [k, Number((v / total).toFixed(3))])
    );

    const zones = Object.entries(normalized).sort((a, b) => b[1] - a[1]);
    const hotZones = zones.slice(0, 3).map(([k]) => k);
    const coldZones = zones.slice(-2).map(([k]) => k);

    const fixSuggestions: string[] = [];
    if ((normalized.cta as number) < 0.15) {
      fixSuggestions.push("Increase CTA size/contrast and move to bottom center.");
    }
    if ((normalized.headline as number) < 0.25) {
      fixSuggestions.push("Shorten headline and add outline/glow.");
    }
    if ((normalized.icons as number) < 0.1) {
      fixSuggestions.push("Move 3 value icons closer to hero product.");
    }

    return {
      attention: normalized,
      hot_zones: hotZones,
      cold_zones: coldZones,
      fix_suggestions: fixSuggestions,
    };
  }
}
