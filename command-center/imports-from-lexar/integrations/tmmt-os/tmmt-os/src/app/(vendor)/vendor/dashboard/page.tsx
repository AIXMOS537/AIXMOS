import Link from "next/link";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { JobStatusBadge } from "@/components/job-status-badge";
import type { VendorJobStatus } from "@/lib/workflow/statuses";
import { formatDate, moneyUSD } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function VendorDashboard() {
  const supabase = createSupabaseServerClient();

  // RLS does the heavy lifting: a vendor sees only their own jobs.
  const { data: jobs } = await supabase
    .from("vendor_jobs")
    .select("id, title, status, offered_price, agreed_price, due_at, location, created_at, cases(ref_code, customer_name)")
    .order("created_at", { ascending: false });

  const groups: Record<string, typeof jobs> = {
    "Action needed": [],
    "Active": [],
    "Finished": [],
  };
  (jobs ?? []).forEach((j: any) => {
    if (["offered"].includes(j.status)) groups["Action needed"]!.push(j);
    else if (["accepted", "scheduled", "in_progress", "pending_review"].includes(j.status)) groups["Active"]!.push(j);
    else groups["Finished"]!.push(j);
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">My jobs</h1>
        <p className="text-sm text-muted-foreground">Accept, update, and close out jobs assigned to you.</p>
      </header>

      {Object.entries(groups).map(([label, list]) => (
        <Card key={label}>
          <CardHeader><CardTitle>{label}</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {!list || list.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nothing here.</p>
            ) : (
              list.map((j: any) => (
                <Link
                  key={j.id}
                  href={`/vendor/jobs/${j.id}`}
                  className="block border rounded-md p-3 hover:bg-accent"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">{j.title}</div>
                      <div className="text-xs text-muted-foreground">
                        {j.cases?.ref_code} · {j.cases?.customer_name ?? "—"}
                        {j.location ? ` · ${j.location}` : ""}
                        {j.due_at ? ` · due ${formatDate(j.due_at)}` : ""}
                        {` · ${moneyUSD(j.agreed_price ?? j.offered_price)}`}
                      </div>
                    </div>
                    <JobStatusBadge status={j.status as VendorJobStatus} />
                  </div>
                </Link>
              ))
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
