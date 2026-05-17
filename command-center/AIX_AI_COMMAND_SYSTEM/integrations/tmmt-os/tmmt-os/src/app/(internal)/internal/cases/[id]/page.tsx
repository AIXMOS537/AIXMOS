import { notFound } from "next/navigation";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { CaseStatusBadge } from "@/components/case-status-badge";
import { JobStatusBadge } from "@/components/job-status-badge";
import { CASE_TRANSITIONS, type CaseStatus, type VendorJobStatus } from "@/lib/workflow/statuses";
import { formatDate, moneyUSD } from "@/lib/utils";
import { advanceCaseAction, assignVendorAction } from "./actions";

export const dynamic = "force-dynamic";

export default async function CaseDetail({ params }: { params: { id: string } }) {
  const supabase = createSupabaseServerClient();

  const { data: c } = await supabase
    .from("cases")
    .select("*")
    .eq("id", params.id)
    .maybeSingle();
  if (!c) notFound();

  const [{ data: history }, { data: jobs }, { data: vendors }] = await Promise.all([
    supabase
      .from("case_status_history")
      .select("from_status, to_status, created_at")
      .eq("case_id", c.id)
      .order("created_at", { ascending: false })
      .limit(20),
    supabase
      .from("vendor_jobs")
      .select("id, title, status, offered_price, agreed_price, due_at, created_at, vendor_id, vendors(company_name)")
      .eq("case_id", c.id)
      .order("created_at", { ascending: false }),
    supabase
      .from("vendors")
      .select("id, company_name, services")
      .eq("active", true)
      .order("company_name"),
  ]);

  const next = CASE_TRANSITIONS[c.status as CaseStatus] ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{c.subject}</h1>
          <p className="text-sm text-muted-foreground">
            {c.ref_code} · {c.customer_name} · {c.request_type} · {formatDate(c.created_at)}
          </p>
        </div>
        <CaseStatusBadge status={c.status as CaseStatus} />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Description</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm whitespace-pre-wrap">
            {c.description || <span className="text-muted-foreground">No details provided.</span>}
            <div className="pt-3 text-xs text-muted-foreground">
              Email: {c.customer_email || "—"} · Phone: {c.customer_phone || "—"}
            </div>
            {c.clickup_task_url && (
              <a className="text-xs underline" href={c.clickup_task_url} target="_blank">View in ClickUp</a>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Advance status</CardTitle></CardHeader>
          <CardContent>
            <form action={advanceCaseAction} className="space-y-3">
              <input type="hidden" name="case_id" value={c.id} />
              <Label htmlFor="to">Next status</Label>
              <Select id="to" name="to" defaultValue={next[0] ?? c.status}>
                {[...next, c.status].map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </Select>
              <Label htmlFor="note">Note (optional)</Label>
              <Textarea id="note" name="note" rows={2} />
              <Button type="submit" className="w-full">Save</Button>
            </form>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Assign a vendor</CardTitle></CardHeader>
        <CardContent>
          <form action={assignVendorAction} className="grid sm:grid-cols-2 gap-3">
            <input type="hidden" name="case_id" value={c.id} />
            <div className="sm:col-span-2">
              <Label htmlFor="vendor_id">Vendor</Label>
              <Select id="vendor_id" name="vendor_id" required>
                {(vendors ?? []).map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.company_name} {v.services?.length ? `· ${v.services.join(", ")}` : ""}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="title">Job title</Label>
              <Input id="title" name="title" required defaultValue={c.subject} />
            </div>
            <div>
              <Label htmlFor="offered_price">Offered price</Label>
              <Input id="offered_price" name="offered_price" type="number" step="0.01" min={0} />
            </div>
            <div className="sm:col-span-2">
              <Label htmlFor="description">Description</Label>
              <Textarea id="description" name="description" rows={3} defaultValue={c.description ?? ""} />
            </div>
            <div>
              <Label htmlFor="due_at">Due at</Label>
              <Input id="due_at" name="due_at" type="datetime-local" />
            </div>
            <div className="sm:col-span-2">
              <Button type="submit">Offer to vendor</Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle>Vendor jobs</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {(jobs ?? []).length === 0 && <p className="text-sm text-muted-foreground">No vendor jobs.</p>}
            {(jobs ?? []).map((j: any) => (
              <div key={j.id} className="border rounded-md p-3 flex items-center justify-between">
                <div>
                  <div className="font-medium">{j.title}</div>
                  <div className="text-xs text-muted-foreground">
                    {j.vendors?.company_name ?? "—"} · {moneyUSD(j.agreed_price ?? j.offered_price)} · due {formatDate(j.due_at)}
                  </div>
                </div>
                <JobStatusBadge status={j.status as VendorJobStatus} />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Status history</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {(history ?? []).map((h, i) => (
              <div key={i} className="flex justify-between border-b last:border-0 py-1">
                <span>
                  {h.from_status ?? "—"} → <span className="font-medium">{h.to_status}</span>
                </span>
                <span className="text-muted-foreground text-xs">{formatDate(h.created_at)}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
