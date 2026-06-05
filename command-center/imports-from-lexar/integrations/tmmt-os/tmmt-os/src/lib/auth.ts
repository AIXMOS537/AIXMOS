import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "./supabase/server";
import type { UserRole } from "./workflow/statuses";

export async function getCurrentUser() {
  const supabase = createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;
  const { data: profile } = await supabase
    .from("profiles")
    .select("id, email, full_name, role, organization_id")
    .eq("id", user.id)
    .maybeSingle();
  return profile ? { ...profile, auth: user } : null;
}

export async function requireRole(roles: UserRole[]) {
  const me = await getCurrentUser();
  if (!me) redirect("/login");
  if (!roles.includes(me.role as UserRole)) redirect("/login?error=forbidden");
  return me;
}
