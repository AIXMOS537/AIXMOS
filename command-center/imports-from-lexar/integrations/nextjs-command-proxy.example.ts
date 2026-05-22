/**
 * Example: proxy from your existing Next.js app on Vercel to the AIX Command API.
 *
 * 1. Copy to: app/api/command/[...path]/route.ts  (App Router)
 *    or:      pages/api/command/[...path].ts       (Pages Router — adapt handler shape)
 *
 * 2. Env on your main Vercel project:
 *    AIX_COMMAND_API_URL=https://your-command-api.vercel.app
 *    COMMAND_API_SECRET=shared-secret
 */

import { NextRequest, NextResponse } from "next/server";

const COMMAND_API = process.env.AIX_COMMAND_API_URL?.replace(/\/$/, "");
const SECRET = process.env.COMMAND_API_SECRET;

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, context: RouteContext) {
  if (!COMMAND_API) {
    return NextResponse.json(
      { error: "AIX_COMMAND_API_URL is not configured" },
      { status: 503 }
    );
  }

  const { path } = await context.params;
  const subpath = path.join("/");
  const url = `${COMMAND_API}/${subpath}${request.nextUrl.search}`;

  const headers = new Headers(request.headers);
  headers.delete("host");
  if (SECRET) {
    headers.set("X-Command-Secret", SECRET);
  }

  const init: RequestInit = {
    method: request.method,
    headers,
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.text();
  }

  const upstream = await fetch(url, init);
  const body = await upstream.text();

  return new NextResponse(body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("Content-Type") ?? "application/json",
    },
  });
}

export const GET = proxy;
export const POST = proxy;
