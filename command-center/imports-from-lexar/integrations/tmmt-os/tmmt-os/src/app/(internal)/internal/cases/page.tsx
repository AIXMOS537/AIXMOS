import Link from "next/link";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table";
import { CaseStatusBadge } from "@/components/case-status-badge";
import { CASE_STATUSES, type CaseStatus } from "@/lib/workflow/statuses";
import { formatDate } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function CasesIndex({ searchParams }: { searchParams: { status?: string } }) {
  const supabase = createSupabaseServerClient();
  let q = supabase
    .from("cases")
    .select("id, ref_code, customer_name, request_type, subject, status, created_at")
    .order("created_at", { ascending: false })
    .limit(200);
  if (searchParams.status && (CASE_STATUSES as readonly string[]).includes(searchParams.status)) {
    q = q.eq("status", searchParams.status);
  }
  const { data: cases } = await q;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Cases</CardTitle>
        <form className="flex items-center gap-2">
          <select
            name="status"
            defaultValue={searchParams.status ?? ""}
            className="h-9 rounded-md border bg-background px-2 text-sm"
          >
            <option value="">All statuses</option>
            {CASE_STATUSES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <button className="text-sm underline" type="submit">Filter</button>
        </form>
      </CardHeader>
      <CardContent>
        <Table>
          <Thead>
            <Tr>
              <Th>Ref</Th>
              <Th>Customer</Th>
              <Th>Request</Th>
              <Th>Subject</Th>
              <Th>Status</Th>
              <Th>Created</Th>
            </Tr>
          </Thead>
          <Tbody>
            {(cases ?? []).map((c) => (
              <Tr key={c.id}>
                <Td className="font-mono text-xs">
                  <Link href={`/internal/cases/${c.id}`} className="underline">{c.ref_code}</Link>
                </Td>
                <Td>{c.customer_name}</Td>
                <Td>{c.request_type}</Td>
                <Td>{c.subject}</Td>
                <Td><CaseStatusBadge status={c.status as CaseStatus} /></Td>
                <Td className="text-muted-foreground text-xs">{formatDate(c.created_at)}</Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </CardContent>
    </Card>
  );
}
