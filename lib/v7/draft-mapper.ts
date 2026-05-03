type WinnerScore = {
  total?: number;
  attention?: number;
  trust?: number;
  conversion?: number;
  visual?: number;
};

export type WinnerCreative = {
  type: string;
  hook: string;
  offer: string;
  cta: string;
  prompt: string;
  score?: WinnerScore;
};

export type MetaDraftPayload = {
  platform: "meta";
  mode: "draft";
  campaign: {
    name: string;
    objective: "OUTCOME_SALES" | "OUTCOME_LEADS" | "OUTCOME_TRAFFIC";
    status: "PAUSED";
    special_ad_categories: string[];
  };
  adSet: {
    name: string;
    optimization_goal: "OFFSITE_CONVERSIONS" | "LEAD_GENERATION" | "LINK_CLICKS";
    billing_event: "IMPRESSIONS";
    daily_budget: number;
    status: "PAUSED";
  };
  creative: {
    name: string;
    headline: string;
    primary_text: string;
    call_to_action: string;
    image_prompt: string;
  };
};

export type TikTokDraftPayload = {
  platform: "tiktok";
  mode: "draft";
  campaign: {
    campaign_name: string;
    objective_type: "CONVERSIONS" | "LEAD_GENERATION" | "TRAFFIC";
    budget_mode: "BUDGET_MODE_DAY";
    budget: number;
  };
  adgroup: {
    adgroup_name: string;
    optimization_goal: "CONVERSIONS" | "LEAD_GENERATION" | "TRAFFIC";
    billing_event: "CPM";
    budget: number;
  };
  creative: {
    ad_name: string;
    text: string;
    call_to_action: string;
    video_script_prompt: string;
  };
};

function objectiveFromGoal(goal: string) {
  const normalized = String(goal || "conversion").toLowerCase();
  if (normalized.includes("lead")) {
    return {
      metaObjective: "OUTCOME_LEADS" as const,
      metaOptimizationGoal: "LEAD_GENERATION" as const,
      tiktokObjective: "LEAD_GENERATION" as const
    };
  }
  if (normalized.includes("click") || normalized.includes("traffic")) {
    return {
      metaObjective: "OUTCOME_TRAFFIC" as const,
      metaOptimizationGoal: "LINK_CLICKS" as const,
      tiktokObjective: "TRAFFIC" as const
    };
  }

  return {
    metaObjective: "OUTCOME_SALES" as const,
    metaOptimizationGoal: "OFFSITE_CONVERSIONS" as const,
    tiktokObjective: "CONVERSIONS" as const
  };
}

function callToActionLabel(raw: string) {
  const text = String(raw || "").toLowerCase();
  if (text.includes("mua")) return "SHOP_NOW";
  if (text.includes("dang ky") || text.includes("đăng ký")) return "SIGN_UP";
  if (text.includes("demo") || text.includes("tu van") || text.includes("tư vấn")) return "LEARN_MORE";
  return "LEARN_MORE";
}

export function mapWinnerToMetaDraft(args: {
  winner: WinnerCreative;
  campaignId: string;
  goal?: string;
  brand?: string;
  budgetDaily?: number;
}): MetaDraftPayload {
  const budget = Math.max(100000, Number(args.budgetDaily || 300000));
  const objective = objectiveFromGoal(args.goal || "conversion");
  const brand = args.brand || "AI Ads Factory";
  const cta = callToActionLabel(args.winner.cta);

  return {
    platform: "meta",
    mode: "draft",
    campaign: {
      name: `${brand} - ${args.winner.type} - ${args.campaignId.slice(0, 8)}`,
      objective: objective.metaObjective,
      status: "PAUSED",
      special_ad_categories: []
    },
    adSet: {
      name: `adset-${args.winner.type}`,
      optimization_goal: objective.metaOptimizationGoal,
      billing_event: "IMPRESSIONS",
      daily_budget: budget,
      status: "PAUSED"
    },
    creative: {
      name: `creative-${args.winner.type}`,
      headline: args.winner.hook,
      primary_text: args.winner.offer,
      call_to_action: cta,
      image_prompt: args.winner.prompt
    }
  };
}

export function mapWinnerToTikTokDraft(args: {
  winner: WinnerCreative;
  campaignId: string;
  goal?: string;
  brand?: string;
  budgetDaily?: number;
}): TikTokDraftPayload {
  const budget = Math.max(100000, Number(args.budgetDaily || 300000));
  const objective = objectiveFromGoal(args.goal || "conversion");
  const brand = args.brand || "AI Ads Factory";

  return {
    platform: "tiktok",
    mode: "draft",
    campaign: {
      campaign_name: `${brand} - ${args.winner.type} - ${args.campaignId.slice(0, 8)}`,
      objective_type: objective.tiktokObjective,
      budget_mode: "BUDGET_MODE_DAY",
      budget
    },
    adgroup: {
      adgroup_name: `adgroup-${args.winner.type}`,
      optimization_goal: objective.tiktokObjective,
      billing_event: "CPM",
      budget
    },
    creative: {
      ad_name: `creative-${args.winner.type}`,
      text: `${args.winner.hook}. ${args.winner.offer}. ${args.winner.cta}`,
      call_to_action: callToActionLabel(args.winner.cta),
      video_script_prompt: args.winner.prompt
    }
  };
}