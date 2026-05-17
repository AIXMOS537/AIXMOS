import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <main className="min-h-screen container py-16 space-y-12">
      <header className="space-y-2">
        <h1 className="text-4xl font-semibold">TMMT OS</h1>
        <p className="text-muted-foreground">
          The business operating system for TMMT Rentals, Ecosystem, and Project AIXMOS.
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle>Submit a request</CardTitle>
            <CardDescription>Anyone can start a case here.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/intake"><Button className="w-full">New intake form</Button></Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Internal team</CardTitle>
            <CardDescription>Cases, tasks, vendor assignment.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/internal/dashboard"><Button variant="outline" className="w-full">Open</Button></Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Vendor portal</CardTitle>
            <CardDescription>Approved vendors: your job queue.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/vendor/dashboard"><Button variant="outline" className="w-full">Open</Button></Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Investor portal</CardTitle>
            <CardDescription>Performance updates & reports.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/investor/dashboard"><Button variant="outline" className="w-full">Open</Button></Link>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
