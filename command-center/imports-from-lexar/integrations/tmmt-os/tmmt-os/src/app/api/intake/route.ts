import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { createSupabaseServiceClient } from "@/lib/supabase/service";
import { REQUEST_TYPES, suggestedNextStatus } from "@/lib/workflow/statuses";

const Body = z.object({
  customer_name: z.string().min(1),
  customer_email: z.string().email().optional(),
  customer_phone: z.string().optional(),
  request_type: z.enum(REQUEST_TYPES).optional(),
  subject: z.string().min(1),
  details: z.string().optional(),
  source: z.string().optional(),
  airtable_id: z.string().optional(),
  payload: z.record(z.any()).optional(),
});

/**
 * Public webhook endpoint for external intake sources (Airtable automation,
 * GoHighLevel webhook, Zapier, n8n, etc.). Gate it with the INTAKE_WEBHOOK_SECRET
 * header so it can't be spammed.
 *
 *   curl -X POST https://YOUR-APP/api/intake \
 *     -H "Content-Type: application/json" \
 *     -H "X-Intake-Secret: $INTAKE_WEBHOOK_SECRET" \
 *     -d '{"customer_name":"Jane","subject":"flat tire","request_type":"tow"}'
 */
export async function POST(req: NextRequest) {
  const secret = process.env.INTAKE_WEBHOOK_SECRET;
  if (secret && req.headers.get("x-intake-secret") !== secret) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const json = await req.json().catch(() => null);
  const parsed = Body.safeParse(json);
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }
  const data = parsed.data;

  const supabase = createSupabaseServiceClient();
  const { data: intake, error: intakeErr } = await supabase
    .from("customer_intake_forms")
    .insert({
      customer_name: data.customer_name,
      customer_email: data.customer_email ?? null,
      customer_phone: data.customer_phone ?? null,
      request_type: data.request_type ?? "other",
      subject: data.subject,
      details: data.details ?? null,
      source: data.source ?? "api",
      airtable_id: data.airtable_id ?? null,
      payload: data.payload ?? {},
    })
    .select("id")
    .single();
  if (intakeErr) return NextResponse.json({ error: intakeErr.message }, { status: 500 });

  const { data: c, error: caseErr } = await supabase
    .from("cases")
    .insert({
      intake_id: intake.id,
      customer_name: data.customer_name,
      customer_email: data.customer_email ?? null,
      customer_phone: data.customer_phone ?? null,
      request_type: data.request_type ?? "other",
      subject: data.subject,
      description: data.details ?? null,
      airtable_id: data.airtable_id ?? null,
      status: suggestedNextStatus(data.request_type ?? "other"),
    })
    .select("id, ref_code, status")
    .single();
  if (caseErr) return NextResponse.json({ error: caseErr.message }, { status: 500 });

  return NextResponse.json({ ok: true, case: c, intake_id: intake.id });
}
