import { createSupabaseServerClient } from "@/lib/supabase/server";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { formatDate, moneyUSD } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function InvestorDashboard() {
  const supabase = createSupabaseServerClient();
  // RLS limits both reads to the investor's organization.
  const [{ data: account }, { data: updates }] = await Promise.all([
    supabase
      .from("investor_accounts")
      .select("display_name, position_value, organization_id, organizations(name)")
      .maybeSingle(),
    supabase
      .from("investor_updates")
      .select("title, body, period_start, period_end, published_at, created_at")
      .eq("published", true)
      .order("created_at", { ascending: false })
      .limit(20),
  ]);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>{(account as any)?.display_name ?? "Investor"}</CardTitle>
          <CardDescription>{(account as any)?.organizations?.name ?? "—"}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-semibold">{moneyUSD((account as any)?.position_value)}</div>
          <div className="text-xs text-muted-foreground">Current position</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Latest updates</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {(updates ?? []).length === 0 && <p className="text-sm text-muted-foreground">No updates yet.</p>}
          {(updates ?? []).map((u, i) => (
            <div key={i} className="border-b last:border-0 py-3">
              <div className="font-medium">{u.title}</div>
              <div className="text-xs text-muted-foreground">
                {u.period_start ? `${u.period_start} – ${u.period_end}` : formatDate(u.created_at)}
              </div>
              {u.body && <p className="text-sm mt-1 whitespace-pre-wrap">{u.body}</p>}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
