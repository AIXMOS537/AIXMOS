import { PortalShell } from "@/components/portal-shell";
import { requireRole } from "@/lib/auth";

export default async function InvestorLayout({ children }: { children: React.ReactNode }) {
  const me = await requireRole(["investor", "admin"]);
  return (
    <PortalShell
      brand="TMMT OS · Investor"
      links={[{ href: "/investor/dashboard", label: "Dashboard" }]}
      user={me}
    >
      {children}
    </PortalShell>
  );
}
