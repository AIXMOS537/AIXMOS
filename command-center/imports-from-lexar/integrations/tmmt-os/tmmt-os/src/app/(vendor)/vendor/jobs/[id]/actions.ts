"use server";

import { revalidatePath } from "next/cache";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { addVendorJobNote, recordVendorFile, setVendorJobStatus } from "@/lib/workflow/engine";
import type { VendorJobStatus } from "@/lib/workflow/statuses";

export async function updateJobStatusAction(formData: FormData) {
  const id = String(formData.get("job_id"));
  const to = String(formData.get("to")) as VendorJobStatus;
  const note = (formData.get("note") as string) || undefined;
  await setVendorJobStatus(id, to, note);
}

export async function addNoteAction(formData: FormData) {
  const id = String(formData.get("job_id"));
  const body = String(formData.get("body") || "").trim();
  if (!body) return;
  await addVendorJobNote(id, body);
}

export async function uploadFileAction(formData: FormData) {
  const id = String(formData.get("job_id"));
  const file = formData.get("file") as File | null;
  const kind = (formData.get("kind") as "photo" | "invoice" | "document") || "photo";
  if (!file || file.size === 0) return;

  const supabase = createSupabaseServerClient();
  const arrayBuffer = await file.arrayBuffer();
  const path = `${id}/${Date.now()}-${file.name.replace(/[^a-zA-Z0-9._-]/g, "_")}`;

  const { error: upErr } = await supabase.storage
    .from("vendor-files")
    .upload(path, new Uint8Array(arrayBuffer), { contentType: file.type, upsert: false });
  if (upErr) throw new Error(upErr.message);

  await recordVendorFile({
    jobId: id,
    storagePath: path,
    filename: file.name,
    mimeType: file.type,
    sizeBytes: file.size,
    kind,
  });
  revalidatePath(`/vendor/jobs/${id}`);
}
