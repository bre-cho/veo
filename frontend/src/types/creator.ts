import type { AvatarDna } from "./avatar";

export interface CreatorEarning {
  id: string;
  creator_id: string;
  avatar_id?: string | null;
  amount_usd: number;
  earning_type?: string | null;
  period_start?: string | null;
  period_end?: string | null;
  payout_status: string;
  created_at?: string | null;
}

export interface CreatorRanking {
  id: string;
  creator_id: string;
  rank_score: number;
  total_earnings_usd: number;
  avatar_count: number;
  last_computed_at?: string | null;
}

export interface CreatorStore {
  creator_id: string;
  avatars: AvatarDna[];
  total_avatars: number;
  total_earnings_usd: number;
}
