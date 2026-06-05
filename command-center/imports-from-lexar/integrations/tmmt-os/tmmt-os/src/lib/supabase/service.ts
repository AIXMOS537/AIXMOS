import { createClient } from "@supabase/supabase-js";

/**
 * Service-role client. BYPASSES RLS. Use only on the server, and only when
 * absolutely necessary (e.g. anonymous /api/intake POSTs, admin scripts).
 * Never import this from a client component.
 */
export function createSupabaseServiceClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    throw new Error("Missing SUPABASE service-role env vars");
  }
  return createClient(url, key, { auth: { persistSession: false } });
}
