export interface AvatarDna {
  id: string;
  name: string;
  role_id?: string | null;
  niche_code?: string | null;
  market_code?: string | null;
  owner_user_id?: string | null;
  creator_id?: string | null;
  is_published: boolean;
  is_featured: boolean;
  tags?: string[] | null;
  meta?: Record<string, unknown> | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AvatarVisualDna {
  id: string;
  avatar_id: string;
  skin_tone?: string | null;
  hair_style?: string | null;
  hair_color?: string | null;
  eye_color?: string | null;
  outfit_code?: string | null;
  background_code?: string | null;
  age_range?: string | null;
  gender_expression?: string | null;
  accessories?: string[] | null;
  reference_image_url?: string | null;
}

export interface AvatarVoiceDna {
  id: string;
  avatar_id: string;
  voice_profile_id?: string | null;
  language_code?: string | null;
  accent_code?: string | null;
  tone?: string | null;
  pitch?: string | null;
  speed?: string | null;
}

export interface AvatarMotionDna {
  id: string;
  avatar_id: string;
  motion_style?: string | null;
  gesture_set?: string | null;
  idle_animation?: string | null;
  lipsync_mode?: string | null;
  blink_rate?: string | null;
}

export interface AvatarRole {
  id: string;
  name: string;
  description?: string | null;
  niche_tags?: string[] | null;
}

export interface AvatarRanking {
  id: string;
  avatar_id: string;
  rank_score: number;
  trending_score: number;
  usage_count_7d: number;
  usage_count_30d: number;
  download_count: number;
  last_computed_at?: string | null;
}
