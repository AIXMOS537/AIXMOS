import { notFound } from "next/navigation";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { JobStatusBadge } from "@/components/job-status-badge";
import { VENDOR_ALLOWED_TRANSITIONS, VENDOR_JOB_LABEL, type VendorJobStatus } from "@/lib/workflow/statuses";
import { formatDate, moneyUSD } from "@/lib/utils";
import { addNoteAction, updateJobStatusAction, uploadFileAction } from "./actions";

export const dynamic = "force-dynamic";

export default async function VendorJobPage({ params }: { params: { id: string } }) {
  const supabase = createSupabaseServerClient();
  const { data: job } = await supabase
    .from("vendor_jobs")
    .select("id, title, description, status, offered_price, agreed_price, due_at, scheduled_for, location, created_at, cases(ref_code, customer_name, customer_email, customer_phone)")
    .eq("id", params.id)
    .maybeSingle();
  if (!job) notFound();

  const [{ data: updates }, { data: files }] = await Promise.all([
    supabase
      .from("vendor_job_updates")
      .select("kind, body, created_at, metadata")
      .eq("vendor_job_id", job.id)
      .order("created_at", { ascending: false })
      .limit(50),
    supabase
      .from("vendor_files")
      .select("id, kind, storage_path, filename, created_at")
      .eq("vendor_job_id", job.id)
      .order("created_at", { ascending: false }),
  ]);

  const allowed = VENDOR_ALLOWED_TRANSITIONS[job.status as VendorJobStatus] ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{job.title}</h1>
          <p className="text-sm text-muted-foreground">
            {(job as any).cases?.ref_code} · {(job as any).cases?.customer_name ?? "—"}
            {job.location ? ` · ${job.location}` : ""}
            {job.due_at ? ` · due ${formatDate(job.due_at)}` : ""}
            {` · ${moneyUSD(job.agreed_price ?? job.offered_price)}`}
          </p>
        </div>
        <JobStatusBadge status={job.status as VendorJobStatus} />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Job details</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm whitespace-pre-wrap">
            {job.description || <span className="text-muted-foreground">No description provided.</span>}
            <div className="pt-3 text-xs text-muted-foreground">
              Customer: {(job as any).cases?.customer_email ?? "—"} {(job as any).cases?.customer_phone ? `· ${(job as any).cases?.customer_phone}` : ""}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Update status</CardTitle></CardHeader>
          <CardContent>
            {allowed.length === 0 ? (
              <p className="text-sm text-muted-foreground">No status changes available — TMMT ops will take it from here.</p>
            ) : (
              <form action={updateJobStatusAction} className="space-y-3">
                <input type="hidden" name="job_id" value={job.id} />
                <Label htmlFor="to">New status</Label>
                <Select id="to" name="to" defaultValue={allowed[0]}>
                  {allowed.map((s) => (
                    <option key={s} value={s}>{VENDOR_JOB_LABEL[s]}</option>
                  ))}
                </Select>
                <Label htmlFor="note">Note</Label>
                <Textarea id="note" name="note" rows={2} placeholder="Optional — let ops know what changed." />
                <Button className="w-full">Save</Button>
              </form>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle>Upload photo / invoice</CardTitle></CardHeader>
          <CardContent>
            <form action={uploadFileAction} encType="multipart/form-data" className="space-y-3">
              <input type="hidden" name="job_id" value={job.id} />
              <div>
                <Label htmlFor="kind">Type</Label>
                <Select id="kind" name="kind" defaultValue="photo">
                  <option value="photo">Photo</option>
                  <option value="invoice">Invoice</option>
                  <option value="document">Document</option>
                </Select>
              </div>
              <div>
                <Label htmlFor="file">File</Label>
                <input
                  id="file"
                  name="file"
                  type="file"
                  required
                  className="block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-secondary file:px-3 file:py-2"
                />
              </div>
              <Button type="submit">Upload</Button>
            </form>

            <div className="mt-4 space-y-2 text-sm">
              {(files ?? []).map((f) => (
                <div key={f.id} className="flex justify-between border-b last:border-0 py-1">
                  <span>{f.kind}: {f.filename}</span>
                  <span className="text-xs text-muted-foreground">{formatDate(f.created_at)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Timeline & notes</CardTitle></CardHeader>
          <CardContent>
            <form action={addNoteAction} className="space-y-2 mb-4">
              <input type="hidden" name="job_id" value={job.id} />
              <Textarea name="body" rows={2} placeholder="Add a note for the TMMT team" />
              <Button size="sm" type="submit">Post note</Button>
            </form>

            <div className="space-y-2 text-sm">
              {(updates ?? []).map((u, i) => (
                <div key={i} className="border-b last:border-0 py-2">
                  <div className="text-xs uppercase text-muted-foreground">{u.kind}</div>
                  <div>{u.body}</div>
                  <div className="text-xs text-muted-foreground">{formatDate(u.created_at)}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
