"use server";

import { revalidatePath } from "next/cache";
import { createSupabaseServerClient } from "../supabase/server";
import { caseStatusForVendorJob, type CaseStatus, type VendorJobStatus } from "./statuses";

/**
 * Workflow engine — thin server-side helpers that move cases & vendor jobs
 * through the pipeline and write an activity log entry. RLS does the auth
 * checking; these helpers do the orchestration.
 */

async function logActivity(
  entity: string,
  entity_id: string,
  action: string,
  data: Record<string, unknown> = {}
) {
  const supabase = createSupabaseServerClient();
  const { data: { user } } = await supabase.auth.getUser();
  await supabase.from("activity_logs").insert({
    actor_id: user?.id ?? null,
    entity,
    entity_id,
    action,
    data,
  });
}

export async function advanceCase(caseId: string, to: CaseStatus, note?: string) {
  const supabase = createSupabaseServerClient();
  const { error } = await supabase
    .from("cases")
    .update({ status: to })
    .eq("id", caseId);
  if (error) throw new Error(error.message);
  await logActivity("case", caseId, "status_changed", { to, note });
  revalidatePath(`/internal/cases/${caseId}`);
  revalidatePath(`/internal/cases`);
  return { ok: true };
}

export async function assignCaseToVendor(args: {
  caseId: string;
  vendorId: string;
  title: string;
  description?: string;
  location?: string;
  offeredPrice?: number;
  dueAt?: string;
}) {
  const supabase = createSupabaseServerClient();
  const { data: job, error } = await supabase
    .from("vendor_jobs")
    .insert({
      case_id: args.caseId,
      vendor_id: args.vendorId,
      title: args.title,
      description: args.description ?? null,
      location: args.location ?? null,
      offered_price: args.offeredPrice ?? null,
      due_at: args.dueAt ?? null,
      status: "offered",
    })
    .select("id")
    .single();
  if (error) throw new Error(error.message);

  await supabase.from("cases").update({ status: "vendor_assigned" }).eq("id", args.caseId);
  await logActivity("vendor_job", job.id, "created", { case_id: args.caseId, vendor_id: args.vendorId });

  // Best-effort notify the vendor profile
  const { data: vendor } = await supabase
    .from("vendors")
    .select("profile_id, company_name")
    .eq("id", args.vendorId)
    .maybeSingle();
  if (vendor?.profile_id) {
    await supabase.from("notifications").insert({
      recipient: vendor.profile_id,
      case_id: args.caseId,
      kind: "vendor_job_offered",
      title: `New job offered: ${args.title}`,
      body: args.description ?? null,
    });
  }

  revalidatePath(`/internal/cases/${args.caseId}`);
  revalidatePath(`/vendor/dashboard`);
  return { jobId: job.id };
}

export async function setVendorJobStatus(jobId: string, to: VendorJobStatus, note?: string) {
  const supabase = createSupabaseServerClient();
  const { data: job, error: getErr } = await supabase
    .from("vendor_jobs")
    .select("id, case_id, status")
    .eq("id", jobId)
    .single();
  if (getErr) throw new Error(getErr.message);

  const { error } = await supabase
    .from("vendor_jobs")
    .update({ status: to })
    .eq("id", jobId);
  if (error) throw new Error(error.message);

  await supabase.from("vendor_job_updates").insert({
    vendor_job_id: jobId,
    kind: "status_change",
    body: `${job.status} → ${to}${note ? ` — ${note}` : ""}`,
  });

  // Reflect into the parent case status when meaningful.
  const mirror = caseStatusForVendorJob(to);
  if (mirror) {
    await supabase.from("cases").update({ status: mirror }).eq("id", job.case_id);
  }

  await logActivity("vendor_job", jobId, "status_changed", { from: job.status, to });
  revalidatePath(`/vendor/jobs/${jobId}`);
  revalidatePath(`/vendor/dashboard`);
  revalidatePath(`/internal/cases/${job.case_id}`);
  return { ok: true };
}

export async function addVendorJobNote(jobId: string, body: string) {
  const supabase = createSupabaseServerClient();
  const { error } = await supabase
    .from("vendor_job_updates")
    .insert({ vendor_job_id: jobId, kind: "note", body });
  if (error) throw new Error(error.message);
  revalidatePath(`/vendor/jobs/${jobId}`);
  return { ok: true };
}

export async function recordVendorFile(args: {
  jobId: string;
  storagePath: string;
  filename: string;
  mimeType: string;
  sizeBytes: number;
  kind?: "photo" | "invoice" | "document";
}) {
  const supabase = createSupabaseServerClient();
  const { error } = await supabase.from("vendor_files").insert({
    vendor_job_id: args.jobId,
    storage_path: args.storagePath,
    filename: args.filename,
    mime_type: args.mimeType,
    size_bytes: args.sizeBytes,
    kind: args.kind ?? "photo",
  });
  if (error) throw new Error(error.message);
  await supabase.from("vendor_job_updates").insert({
    vendor_job_id: args.jobId,
    kind: args.kind ?? "photo",
    body: `Uploaded ${args.filename}`,
    metadata: { storage_path: args.storagePath },
  });
  revalidatePath(`/vendor/jobs/${args.jobId}`);
  return { ok: true };
}
