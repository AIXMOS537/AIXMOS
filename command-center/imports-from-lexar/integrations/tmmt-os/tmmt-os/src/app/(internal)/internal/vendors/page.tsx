import { createSupabaseServerClient } from "@/lib/supabase/server";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

export const dynamic = "force-dynamic";

export default async function VendorsAdmin() {
  const supabase = createSupabaseServerClient();
  const { data: vendors } = await supabase
    .from("vendors")
    .select("id, company_name, contact_name, email, phone, services, active, created_at")
    .order("company_name");

  return (
    <Card>
      <CardHeader><CardTitle>Vendors</CardTitle></CardHeader>
      <CardContent>
        <Table>
          <Thead>
            <Tr>
              <Th>Company</Th>
              <Th>Contact</Th>
              <Th>Services</Th>
              <Th>Status</Th>
            </Tr>
          </Thead>
          <Tbody>
            {(vendors ?? []).map((v) => (
              <Tr key={v.id}>
                <Td>{v.company_name}</Td>
                <Td>
                  <div>{v.contact_name ?? "—"}</div>
                  <div className="text-xs text-muted-foreground">{v.email ?? ""} {v.phone ? `· ${v.phone}` : ""}</div>
                </Td>
                <Td>{(v.services ?? []).join(", ") || "—"}</Td>
                <Td>{v.active ? <Badge variant="success">Active</Badge> : <Badge variant="outline">Inactive</Badge>}</Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
        <p className="text-xs text-muted-foreground mt-4">
          To add a vendor: create their auth user, then in Supabase set <code>profiles.role = &apos;vendor&apos;</code> and insert a row in <code>vendors</code> with their <code>profile_id</code>.
        </p>
      </CardContent>
    </Card>
  );
}
