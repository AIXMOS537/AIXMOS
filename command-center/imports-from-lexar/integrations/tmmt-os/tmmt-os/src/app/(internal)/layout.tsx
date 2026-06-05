import { PortalShell } from "@/components/portal-shell";
import { requireRole } from "@/lib/auth";

export default async function InternalLayout({ children }: { children: React.ReactNode }) {
  const me = await requireRole(["admin", "internal_team"]);
  return (
    <PortalShell
      brand="TMMT OS · Internal"
      links={[
        { href: "/internal/dashboard", label: "Dashboard" },
        { href: "/internal/cases", label: "Cases" },
        { href: "/internal/vendors", label: "Vendors" },
      ]}
      user={me}
    >
      {children}
    </PortalShell>
  );
}
