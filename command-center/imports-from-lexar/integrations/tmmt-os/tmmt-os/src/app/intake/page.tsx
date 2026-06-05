import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { REQUEST_TYPES } from "@/lib/workflow/statuses";
import { submitIntakeAction } from "./actions";

const LABELS: Record<string, string> = {
  rental_booking: "Rental booking",
  rental_support: "Rental support / change",
  maintenance: "Maintenance",
  repair: "Repair",
  detail: "Detail / cleaning",
  tow: "Tow",
  inspection: "Inspection",
  delivery: "Delivery / driver",
  content: "Content / media",
  consulting: "Consulting / coaching",
  other: "Other",
};

export default function IntakePage({ searchParams }: { searchParams: { error?: string } }) {
  return (
    <main className="min-h-screen container py-12 max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>Submit a request</CardTitle>
          <CardDescription>
            Tell us what you need. We'll create a case, route it to the right team, and follow up.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {searchParams.error && (
            <p className="text-sm text-destructive mb-4">{searchParams.error}</p>
          )}
          <form action={submitIntakeAction} className="space-y-4">
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="customer_name">Your name *</Label>
                <Input id="customer_name" name="customer_name" required />
              </div>
              <div>
                <Label htmlFor="customer_email">Email</Label>
                <Input id="customer_email" name="customer_email" type="email" />
              </div>
              <div>
                <Label htmlFor="customer_phone">Phone</Label>
                <Input id="customer_phone" name="customer_phone" type="tel" />
              </div>
              <div>
                <Label htmlFor="request_type">Request type *</Label>
                <Select id="request_type" name="request_type" defaultValue="other" required>
                  {REQUEST_TYPES.map((rt) => (
                    <option key={rt} value={rt}>{LABELS[rt] ?? rt}</option>
                  ))}
                </Select>
              </div>
            </div>
            <div>
              <Label htmlFor="subject">Short subject *</Label>
              <Input id="subject" name="subject" required maxLength={200} placeholder="e.g. Brake noise on Tesla Model 3" />
            </div>
            <div>
              <Label htmlFor="details">Details</Label>
              <Textarea id="details" name="details" rows={6} placeholder="When did it start? Pickup address? Anything else we should know?" />
            </div>
            <Button type="submit" size="lg" className="w-full">Submit request</Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
