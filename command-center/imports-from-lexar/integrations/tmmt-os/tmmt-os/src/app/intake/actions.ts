"use server";

import { z } from "zod";
import { redirect } from "next/navigation";
import { createSupabaseServiceClient } from "@/lib/supabase/service";
import { REQUEST_TYPES, suggestedNextStatus } from "@/lib/workflow/statuses";

const IntakeSchema = z.object({
  customer_name: z.string().min(1).max(200),
  customer_email: z.string().email().optional().or(z.literal("")),
  customer_phone: z.string().max(40).optional().or(z.literal("")),
  request_type: z.enum(REQUEST_TYPES).default("other"),
  subject: z.string().min(1).max(200),
  details: z.string().max(5000).optional().or(z.literal("")),
});

export async function submitIntakeAction(formData: FormData) {
  const parsed = IntakeSchema.safeParse({
    customer_name: formData.get("customer_name"),
    customer_email: formData.get("customer_email") || undefined,
    customer_phone: formData.get("customer_phone") || undefined,
    request_type: (formData.get("request_type") as string) || "other",
    subject: formData.get("subject"),
    details: formData.get("details") || undefined,
  });
  if (!parsed.success) {
    redirect("/intake?error=" + encodeURIComponent(parsed.error.issues[0].message));
  }
  const data = parsed.data;

  // Service client because intake is anonymous (no session). RLS still allows
  // INSERT into customer_intake_forms for anyone, but we use the service client
  // so we can also create the corresponding case row in one server hop.
  const supabase = createSupabaseServiceClient();

  const { data: intake, error: intakeErr } = await supabase
    .from("customer_intake_forms")
    .insert({
      customer_name: data.customer_name,
      customer_email: data.customer_email || null,
      customer_phone: data.customer_phone || null,
      request_type: data.request_type,
      subject: data.subject,
      details: data.details || null,
      source: "web",
      payload: { from: "intake-form" },
    })
    .select("id")
    .single();
  if (intakeErr || !intake) {
    redirect("/intake?error=" + encodeURIComponent(intakeErr?.message ?? "insert failed"));
  }

  const { data: c, error: caseErr } = await supabase
    .from("cases")
    .insert({
      intake_id: intake.id,
      customer_name: data.customer_name,
      customer_email: data.customer_email || null,
      customer_phone: data.customer_phone || null,
      request_type: data.request_type,
      subject: data.subject,
      description: data.details || null,
      status: suggestedNextStatus(data.request_type),
    })
    .select("ref_code")
    .single();
  if (caseErr) {
    redirect("/intake?error=" + encodeURIComponent(caseErr.message));
  }

  await supabase.from("activity_logs").insert({
    entity: "case",
    entity_id: null,
    action: "intake_created",
    data: { intake_id: intake.id, request_type: data.request_type, ref_code: c?.ref_code },
  });

  redirect(`/intake/thanks?ref=${encodeURIComponent(c?.ref_code ?? "")}`);
}
