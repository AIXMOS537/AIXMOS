import { NextResponse } from "next/server";

/**
 * JSON health check for AIX Command System snapshots and uptime monitors.
 * Public — no auth required.
 */
export async function GET() {
  return NextResponse.json({
    ok: true,
    service: "tmmt-os",
    version: process.env.npm_package_version ?? "0.1.0",
    timestamp: new Date().toISOString(),
  });
}
