export interface LocalizationProfile {
  id: string;
  market_code: string;
  country_name: string;
  language_code?: string | null;
  currency_code?: string | null;
  timezone?: string | null;
  rtl: boolean;
  preferred_niches?: string[] | null;
  preferred_roles?: string[] | null;
}

export interface TemplateFamily {
  id: string;
  name: string;
  content_goal?: string | null;
  niche_tags?: string[] | null;
  market_codes?: string[] | null;
  description?: string | null;
  is_active: boolean;
}

export interface ContentGoalClassification {
  content_goal: string;
  confidence: number;
}

export const CONTENT_GOALS = [
  "product_demo",
  "brand_awareness",
  "lead_generation",
  "education",
  "entertainment",
  "sales",
  "testimonial",
] as const;

export type ContentGoal = (typeof CONTENT_GOALS)[number];
