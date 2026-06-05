"use server";
import { advanceCase, assignCaseToVendor } from "@/lib/workflow/engine";
import type { CaseStatus } from "@/lib/workflow/statuses";

export async function advanceCaseAction(formData: FormData) {
  const id = String(formData.get("case_id"));
  const to = String(formData.get("to")) as CaseStatus;
  const note = (formData.get("note") as string) || undefined;
  await advanceCase(id, to, note);
}

export async function assignVendorAction(formData: FormData) {
  const caseId = String(formData.get("case_id"));
  const vendorId = String(formData.get("vendor_id"));
  const title = String(formData.get("title"));
  const description = (formData.get("description") as string) || undefined;
  const offered = formData.get("offered_price");
  const dueAt = (formData.get("due_at") as string) || undefined;
  await assignCaseToVendor({
    caseId,
    vendorId,
    title,
    description,
    offeredPrice: offered ? Number(offered) : undefined,
    dueAt,
  });
}
