import { PosterPublishRequest, WinnerDNAGateResult, WinnerDNAMatch } from "./types";
import { WinnerDNALoader } from "./data";

function tokens(text: string): Set<string> {
  const matches = (text || "").toLowerCase().match(/\w+/gu) || [];
  return new Set(matches);
}

function jaccardSimilarity(a: string, b: string): number {
  const ta = tokens(a);
  const tb = tokens(b);

  if (ta.size === 0 || tb.size === 0) {
    return 0;
  }

  const intersection = new Set([...ta].filter((x) => tb.has(x)));
  const union = new Set([...ta, ...tb]);

  return intersection.size / union.size;
}

export class WinnerDNARecallGate {
  private minSimilarity = 0.42;
  private loader = new WinnerDNALoader();

  evaluate(poster: PosterPublishRequest): WinnerDNAGateResult {
    const winners = this.loader.byIndustry(poster.industry);

    if (winners.length === 0) {
      return {
        poster_id: poster.poster_id,
        industry: poster.industry,
        pass_gate: false,
        decision: "fix_required",
        best_match: undefined,
        required_fixes: [
          `Chưa có Winner DNA cho ngành '${poster.industry}'. Cần chạy test hoặc dùng preset ngành trước khi publish.`,
          "Tạo 3 biến thể hook/visual/CTA rồi chạy A/B test để tạo Winner DNA đầu tiên.",
        ],
        recalled_winners_count: 0,
        rule: "NO DNA MATCH → BLOCK",
      };
    }

    // Find best matching winner
    let bestMatch: WinnerDNAMatch | null = null;
    let bestScore = 0;

    for (const winner of winners) {
      const hookSim = jaccardSimilarity(poster.headline, winner.hook);
      const visualSim = jaccardSimilarity(
        poster.visual_concept,
        winner.visual_concept
      );
      const ctaSim = jaccardSimilarity(poster.cta, winner.cta);

      // Weighted average
      const avgSim = (hookSim + visualSim + ctaSim) / 3;

      if (avgSim > bestScore) {
        bestScore = avgSim;
        bestMatch = {
          dna_id: winner.dna_id,
          industry: winner.industry,
          hook: winner.hook,
          visual_concept: winner.visual_concept,
          cta: winner.cta,
          score: winner.metadata?.winner_rate
            ? parseFloat(winner.metadata.winner_rate) / 100
            : 0.8,
          similarity: avgSim,
          reason: `Hook match: ${(hookSim * 100).toFixed(0)}%, Visual: ${(visualSim * 100).toFixed(0)}%, CTA: ${(ctaSim * 100).toFixed(0)}%`,
        };
      }
    }

    // Decision logic
    let pass_gate = false;
    let decision: "publish" | "fix_required" | "reject" = "reject";
    const fixes: string[] = [];

    if (bestMatch && bestMatch.similarity >= this.minSimilarity) {
      pass_gate = true;
      decision = "publish";
    } else if (bestMatch) {
      decision = "fix_required";
      fixes.push(
        `Poster không khớp với Winner DNA đủ (độ tương đồng ${(bestMatch.similarity * 100).toFixed(1)}% < ngưỡng ${(this.minSimilarity * 100).toFixed(0)}%)`
      );
      fixes.push(`Tham khảo: ${bestMatch.reason}`);
      fixes.push("Sửa headline, visual hoặc CTA để khớp hơn với winning pattern");
    } else {
      decision = "reject";
      fixes.push("Không tìm thấy Winner DNA phù hợp cho poster này");
    }

    return {
      poster_id: poster.poster_id,
      industry: poster.industry,
      pass_gate,
      decision,
      best_match: bestMatch || undefined,
      required_fixes: fixes,
      recalled_winners_count: winners.length,
      rule: "NO DNA MATCH → BLOCK",
    };
  }
}

export class PublishQAOrchestrator {
  private gate = new WinnerDNARecallGate();

  checkBeforePublish(poster: PosterPublishRequest) {
    // Final orchestration before publish
    const dnaResult = this.gate.evaluate(poster);

    // Could integrate with Poster QA here if needed
    // const qaResult = new PosterQAAutoCheck().check(posterData);

    return {
      poster_id: poster.poster_id,
      ready_to_publish: dnaResult.pass_gate,
      dna_check: dnaResult,
      // qa_check would go here
      final_decision: dnaResult.decision,
      all_fixes_required: dnaResult.required_fixes,
    };
  }
}
