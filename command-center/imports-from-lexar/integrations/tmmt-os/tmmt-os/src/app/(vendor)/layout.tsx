import { PortalShell } from "@/components/portal-shell";
import { requireRole } from "@/lib/auth";

export default async function VendorLayout({ children }: { children: React.ReactNode }) {
  const me = await requireRole(["vendor", "admin"]);
  return (
    <PortalShell
      brand="TMMT OS · Vendor"
      links={[{ href: "/vendor/dashboard", label: "My jobs" }]}
      user={me}
    >
      {children}
    </PortalShell>
  );
}
