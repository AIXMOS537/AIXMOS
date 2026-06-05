import { createSupabaseServerClient } from "@/lib/supabase/server";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";
import { CaseStatusBadge } from "@/components/case-status-badge";
import { formatDate } from "@/lib/utils";
import type { CaseStatus } from "@/lib/workflow/statuses";

export const dynamic = "force-dynamic";

export default async function InternalDashboard() {
  const supabase = createSupabaseServerClient();

  const [{ data: openCases }, { data: vendorJobs }] = await Promise.all([
    supabase
      .from("cases")
      .select("id, ref_code, customer_name, subject, status, created_at")
      .not("status", "in", "(completed,closed)")
      .order("created_at", { ascending: false })
      .limit(10),
    supabase
      .from("vendor_jobs")
      .select("id, title, status, case_id, vendor_id, due_at, created_at")
      .in("status", ["offered", "accepted", "scheduled", "in_progress", "pending_review"])
      .order("created_at", { ascending: false })
      .limit(10),
  ]);

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold">Operations dashboard</h1>
        <p className="text-sm text-muted-foreground">Live cases and vendor work in flight.</p>
      </header>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Open cases</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {(openCases ?? []).length === 0 && (
              <p className="text-sm text-muted-foreground">No open cases. Quiet day.</p>
            )}
            {(openCases ?? []).map((c) => (
              <Link
                key={c.id}
                href={`/internal/cases/${c.id}`}
                className="block border rounded-md p-3 hover:bg-accent"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">{c.subject}</div>
                    <div className="text-xs text-muted-foreground">
                      {c.ref_code} · {c.customer_name} · {formatDate(c.created_at)}
                    </div>
                  </div>
                  <CaseStatusBadge status={c.status as CaseStatus} />
                </div>
              </Link>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Vendor work in flight</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {(vendorJobs ?? []).length === 0 && (
              <p className="text-sm text-muted-foreground">No active vendor jobs.</p>
            )}
            {(vendorJobs ?? []).map((j) => (
              <Link
                key={j.id}
                href={`/internal/cases/${j.case_id}`}
                className="block border rounded-md p-3 hover:bg-accent"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">{j.title}</div>
                    <div className="text-xs text-muted-foreground">
                      Due {formatDate(j.due_at)}
                    </div>
                  </div>
                  <span className="text-xs uppercase">{j.status}</span>
                </div>
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
