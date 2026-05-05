import {
  PosterInput,
  QACheckResult,
  QAIssue,
} from "./types";
import { HARDLOCK_RULES, getIndustryRules } from "./rules";

export class PosterQAAutoCheck {
  check(poster: PosterInput): QACheckResult {
    const issues: QAIssue[] = [];
    const checklist: Record<string, boolean> = {};

    // Run all hardlock rules
    for (const rule of HARDLOCK_RULES) {
      const passed = rule.check(poster);
      checklist[rule.rule_id] = passed;

      if (!passed) {
        issues.push({
          rule_id: rule.rule_id,
          severity: rule.severity as any,
          message: rule.message,
          fix: rule.fix,
        });
      }
    }

    // Calculate score (0-100)
    const blockerCount = issues.filter((i) => i.severity === "blocker").length;
    const majorCount = issues.filter((i) => i.severity === "major").length;
    const score = Math.max(
      0,
      100 - blockerCount * 20 - majorCount * 8
    );

    // Determine decision
    let decision: "publish" | "fix_required" | "reject" = "publish";
    if (blockerCount > 0) {
      decision = "reject";
    } else if (majorCount > 0 || score < 70) {
      decision = "fix_required";
    }

    const pass_qa = decision === "publish";

    return {
      poster_id: poster.poster_id,
      pass_qa,
      score,
      issues,
      checklist,
      decision,
    };
  }
}

export class AutoFixPosterAI {
  fix(poster: PosterInput) {
    const industry = poster.industry || "custom";
    const rules = getIndustryRules(industry);

    return {
      poster_id: poster.poster_id,
      rewritten_headline:
        poster.headline || "Sản phẩm chất lượng cao - Giải pháp tôi cần",
      rewritten_cta:
        poster.slogan_or_cta || rules.ctas[0] || "Inbox ngay",
      required_icons: poster.value_icons.length < 3
        ? [...poster.value_icons, ...rules.icons.slice(0, 3 - poster.value_icons.length)]
        : poster.value_icons,
      layout_fix: [
        "Đảm bảo brand logo ở vị trí cao",
        "Product focus ở giữa",
        "CTA button ở dưới cùng",
      ],
      color_lighting_fix: [
        `Đề xuất màu: ${rules.colors.join(", ")}`,
        "Lighting: high-key, focused on product",
      ],
      prompt_patch: "Add professional studio lighting and clear product focus",
      negative_prompt_patch:
        "Remove cluttered backgrounds and unfocused subjects",
    };
  }
}

export class LiveCTROptimizer {
  optimize(metric: any) {
    const ctr = metric.clicks / Math.max(metric.impressions, 1);
    const leadRate = metric.leads / Math.max(metric.clicks, 1);
    const roas = metric.revenue / Math.max(metric.spend, 0.01);

    let action: "scale" | "iterate" | "kill" = "iterate";
    if (ctr > 0.05 && roas > 3) {
      action = "scale";
    } else if (ctr < 0.01 || roas < 0.5) {
      action = "kill";
    }

    return {
      poster_id: metric.poster_id,
      ctr,
      lead_rate: leadRate,
      roas,
      optimizer_score: (ctr * 100 + leadRate * 10 + roas * 5) / 115,
      action,
      recommended_fix: [
        action === "scale"
          ? "Scale budget +50% ngay"
          : "Test sửa headline hoặc visual",
      ],
    };
  }
}

export class AutoVideoFromPoster {
  build(request: any) {
    return {
      poster_id: request.poster.poster_id,
      scenes: [
        {
          type: "product_focus",
          duration: Math.floor(request.duration_seconds * 0.5),
          content: "Product showcase with zoom-in animation",
        },
        {
          type: "value_icons",
          duration: Math.floor(request.duration_seconds * 0.3),
          content: "Value icons with fade transitions",
        },
        {
          type: "cta",
          duration: Math.floor(request.duration_seconds * 0.2),
          content: "CTA button with call-to-action overlay",
        },
      ],
      render_payload: {
        duration: request.duration_seconds,
        aspect_ratio: request.aspect_ratio,
        provider: request.provider,
        template: "default_commerce_v1",
      },
      provider: request.provider,
    };
  }
}
