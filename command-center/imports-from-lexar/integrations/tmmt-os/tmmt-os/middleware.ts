import { NextResponse, type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

const PORTAL_ROLES: Record<string, string[]> = {
  "/internal": ["admin", "internal_team"],
  "/vendor": ["vendor", "admin"],
  "/investor": ["investor", "admin"],
};

export async function middleware(request: NextRequest) {
  // Public assets / Next internals always pass through.
  const { pathname } = request.nextUrl;
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api/intake") || // public webhook
    pathname.startsWith("/api/status") || // public JSON health (command system)
    pathname === "/favicon.ico" ||
    pathname.startsWith("/public")
  ) {
    return NextResponse.next();
  }

  const { response, user, role } = await updateSession(request);

  // Public routes
  const isPublic =
    pathname === "/" ||
    pathname.startsWith("/intake") ||
    pathname.startsWith("/login") ||
    pathname.startsWith("/auth");
  if (isPublic) return response;

  // Authenticated routes require a session
  if (!user) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Role-gate the three portal segments
  for (const prefix of Object.keys(PORTAL_ROLES)) {
    if (pathname.startsWith(prefix)) {
      const allowed = PORTAL_ROLES[prefix];
      if (!role || !allowed.includes(role)) {
        return NextResponse.redirect(new URL("/login?error=forbidden", request.url));
      }
    }
  }

  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
