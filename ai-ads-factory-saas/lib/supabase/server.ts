import { createClient } from "@supabase/supabase-js";

function getEnv(name: string) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing env: ${name}`);
  }
  return value;
}

export function createSupabaseServiceClient() {
  const url = getEnv("NEXT_PUBLIC_SUPABASE_URL");
  const key = getEnv("SUPABASE_SERVICE_ROLE_KEY");
  return createClient(url, key, {
    auth: {
      autoRefreshToken: false,
      persistSession: false
    }
  });
}
