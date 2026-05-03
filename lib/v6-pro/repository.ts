import { createSupabaseServiceClient } from "@/lib/supabase/server";
import type { V6ProScoredVariant } from "@/lib/v6-pro/runtime";

type CampaignRecord = {
  id: string;
  industry: string;
  goal: string;
  input: Record<string, unknown>;
  brain: Record<string, unknown>;
  variants: Record<string, V6ProScoredVariant>;
  winner: V6ProScoredVariant | null;
  created_at: string;
};

type WinnerRecord = {
  id: string;
  campaign_id: string;
  type: string;
  hook: string;
  offer: string;
  cta: string;
  prompt: string;
  score: Record<string, unknown>;
  created_at: string;
};

const memory = {
  campaigns: [] as CampaignRecord[],
  winners: [] as WinnerRecord[]
};

function nextId() {
  return crypto.randomUUID();
}

function hasSupabasePersistence() {
  return Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY);
}

export async function createCampaignRecord(result: {
  industry: string;
  input: Record<string, unknown>;
  brain: Record<string, unknown>;
  scored_variants: Record<string, V6ProScoredVariant>;
  winner: V6ProScoredVariant | null;
}) {
  const record: CampaignRecord = {
    id: nextId(),
    industry: result.industry,
    goal: String(result.brain?.goal || "conversion"),
    input: result.input,
    brain: result.brain,
    variants: result.scored_variants,
    winner: result.winner,
    created_at: new Date().toISOString()
  };

  if (!hasSupabasePersistence()) {
    memory.campaigns.unshift(record);
    return record;
  }

  const supabase = createSupabaseServiceClient();
  const { data, error } = await supabase
    .from("campaigns")
    .insert(record)
    .select("id, industry, goal, input, brain, variants, winner, created_at")
    .single();

  if (error || !data) {
    throw new Error(error?.message || "Cannot create campaign record");
  }

  return data as CampaignRecord;
}

export async function listCampaigns() {
  if (!hasSupabasePersistence()) {
    return memory.campaigns;
  }

  const supabase = createSupabaseServiceClient();
  const { data, error } = await supabase
    .from("campaigns")
    .select("id, industry, goal, winner, created_at")
    .order("created_at", { ascending: false })
    .limit(100);

  if (error) {
    throw new Error(error.message);
  }

  return data || [];
}

export async function getCampaign(id: string) {
  if (!hasSupabasePersistence()) {
    return memory.campaigns.find((campaign) => campaign.id === id) || null;
  }

  const supabase = createSupabaseServiceClient();
  const { data, error } = await supabase
    .from("campaigns")
    .select("*")
    .eq("id", id)
    .maybeSingle();

  if (error) {
    throw new Error(error.message);
  }

  return data || null;
}

export async function saveWinnerDNA(winner: V6ProScoredVariant, campaignId: string) {
  const record: WinnerRecord = {
    id: nextId(),
    campaign_id: campaignId,
    type: winner.type,
    hook: winner.hook,
    offer: winner.offer,
    cta: winner.cta,
    prompt: winner.prompt,
    score: winner.score,
    created_at: new Date().toISOString()
  };

  if (!hasSupabasePersistence()) {
    memory.winners.unshift(record);
    return record;
  }

  const supabase = createSupabaseServiceClient();
  const { data, error } = await supabase
    .from("winner_dna")
    .insert(record)
    .select("*")
    .single();

  if (error || !data) {
    throw new Error(error?.message || "Cannot save winner DNA");
  }

  return data as WinnerRecord;
}

export async function listWinnerDNA() {
  if (!hasSupabasePersistence()) {
    return memory.winners;
  }

  const supabase = createSupabaseServiceClient();
  const { data, error } = await supabase
    .from("winner_dna")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(100);

  if (error) {
    throw new Error(error.message);
  }

  return data || [];
}