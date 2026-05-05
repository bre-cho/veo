import { AdPerformanceEvent, WeightModel } from "./types";
import { MODEL, readJson, writeJson } from "./storage";

const DEFAULT_MODEL: WeightModel = {
  version: "v1",
  weights: {
    ctr: 35,
    lead_rate: 25,
    sale_rate: 20,
    roas: 15,
    predicted_score: 5,
  },
  thresholds: {
    scale_ctr: 0.028,
    kill_ctr: 0.025,
    scale_score: 90,
    learn_score: 85,
  },
  sample_count: 0,
};

export class SelfLearningScoreModel {
  async load(): Promise<WeightModel> {
    const model = await readJson(MODEL, DEFAULT_MODEL);
    await writeJson(MODEL, model);
    return model;
  }

  metrics(e: AdPerformanceEvent) {
    const ctr = e.impressions ? e.clicks / e.impressions : 0;
    const leadRate = e.clicks ? e.leads / e.clicks : 0;
    const saleRate = e.leads ? e.sales / e.leads : 0;
    const roas = e.spend ? e.revenue / e.spend : 0;
    return { ctr, leadRate, saleRate, roas };
  }

  async score(e: AdPerformanceEvent) {
    const model = await this.load();
    const w = model.weights;
    const { ctr, leadRate, saleRate, roas } = this.metrics(e);

    const score =
      Math.min(ctr * 1000, w.ctr) +
      Math.min(leadRate * 100, w.lead_rate) +
      Math.min(saleRate * 100, w.sale_rate) +
      Math.min(roas * 5, w.roas) +
      Math.min((e.predicted_score || 0) / 100 * w.predicted_score, w.predicted_score);

    return {
      score: Number(score.toFixed(2)),
      ctr,
      leadRate,
      saleRate,
      roas,
    };
  }

  async updateWeights(events: AdPerformanceEvent[]): Promise<WeightModel> {
    const model = await this.load();
    if (events.length === 0) {
      return model;
    }

    const losers = [] as AdPerformanceEvent[];
    const winners = [] as AdPerformanceEvent[];

    for (const e of events) {
      const scored = await this.score(e);
      if (
        scored.ctr >= model.thresholds.scale_ctr &&
        scored.score >= model.thresholds.learn_score
      ) {
        winners.push(e);
      } else if (scored.ctr < model.thresholds.kill_ctr) {
        losers.push(e);
      }
    }

    if (
      losers.length > 0 &&
      losers.reduce((sum, e) => sum + e.predicted_score, 0) / losers.length > 85
    ) {
      model.weights.predicted_score = Math.max(2, model.weights.predicted_score - 1);
      model.weights.ctr = Math.min(40, model.weights.ctr + 1);
    }

    if (winners.length > 0) {
      model.weights.ctr = Math.min(40, model.weights.ctr + 0.5);
      model.weights.lead_rate = Math.min(30, model.weights.lead_rate + 0.25);
    }

    model.sample_count += events.length;
    await writeJson(MODEL, model);
    return model;
  }
}
