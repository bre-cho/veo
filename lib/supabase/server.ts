import { createClient } from "@supabase/supabase-js";

function requireEnv(name: string) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing ${name}`);
  }
  return value;
}

export function getSupabaseAnonClient() {
  return createClient(
    requireEnv("NEXT_PUBLIC_SUPABASE_URL"),
    requireEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
  );
}

export function getSupabaseServiceClient() {
  return createClient(
    requireEnv("NEXT_PUBLIC_SUPABASE_URL"),
    requireEnv("SUPABASE_SERVICE_ROLE_KEY")
  );
}

export async function getUserFromBearer(req: Request) {
  const auth = req.headers.get("authorization") || "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7).trim() : "";

  if (!token) {
    return { user: null, token: null, error: "Missing bearer token" };
  }

  const supabase = getSupabaseAnonClient();
  const { data, error } = await supabase.auth.getUser(token);

  if (error || !data.user) {
    return { user: null, token: null, error: "Invalid token" };
  }

  return { user: data.user, token, error: null };
}
