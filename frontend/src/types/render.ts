// Autovis-extended render types
export interface AvatarRenderContext {
  avatar_id?: string | null;
  market_code?: string | null;
  content_goal?: string | null;
  conversion_mode?: string | null;
}

export interface AvatarTemplateFit {
  avatar_id: string;
  template_family_id: string;
  fit_score?: number | null;
}

export interface PerformanceSnapshot {
  id: string;
  avatar_id: string;
  snapshot_date: string;
  views_count: number;
  uses_count: number;
  downloads_count: number;
  earnings_usd: number;
  conversion_rate?: number | null;
}
