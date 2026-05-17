import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ThanksPage({ searchParams }: { searchParams: { ref?: string } }) {
  return (
    <main className="min-h-screen container py-12 max-w-xl">
      <Card>
        <CardHeader>
          <CardTitle>Request received</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p>Thanks — we got your request and created a case. We'll be in touch shortly.</p>
          {searchParams.ref && (
            <p className="text-sm text-muted-foreground">
              Your reference number: <span className="font-mono font-medium">{searchParams.ref}</span>
            </p>
          )}
          <p className="pt-4 text-sm">
            <Link href="/" className="underline">Back to home</Link>
          </p>
        </CardContent>
      </Card>
    </main>
  );
}
