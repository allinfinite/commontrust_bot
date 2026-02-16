import { NextResponse } from "next/server";

import { adminCookieName, adminMaxAgeSeconds, mintAdminCookieValue } from "@/lib/admin_auth";

export const runtime = "nodejs";

/** Build the public-facing origin using reverse-proxy headers, falling back to req.url. */
function externalOrigin(req: Request): string {
  const h = (name: string) => req.headers.get(name);
  const proto = h("x-forwarded-proto") || new URL(req.url).protocol.replace(":", "");
  const host = h("x-forwarded-host") || h("host") || new URL(req.url).host;
  return `${proto}://${host}`;
}

function badRedirect(req: Request, nextPath: string, err: string): NextResponse {
  const url = new URL("/admin/login", externalOrigin(req));
  url.searchParams.set("next", nextPath);
  url.searchParams.set("err", err);
  return NextResponse.redirect(url, { status: 303 });
}

export async function GET(req: Request) {
  return NextResponse.redirect(new URL("/admin/login", externalOrigin(req)), { status: 303 });
}

export async function POST(req: Request) {
  const body = await req.text().catch(() => "");
  const params = new URLSearchParams(body);
  const password = String(params.get("password") ?? "");
  const nextRaw = String(params.get("next") ?? "/admin");
  const nextPath = nextRaw.startsWith("/") ? nextRaw : "/admin";

  const expected = process.env.ADMIN_PASSWORD || "";
  const secret = process.env.ADMIN_COOKIE_SECRET || "";
  if (!expected || !secret) {
    return badRedirect(req, nextPath, "Admin auth is not configured on the server.");
  }

  if (password !== expected) {
    return badRedirect(req, nextPath, "Invalid password.");
  }

  const origin = externalOrigin(req);
  const value = await mintAdminCookieValue(secret);
  const res = NextResponse.redirect(new URL(nextPath, origin), { status: 303 });
  res.cookies.set({
    name: adminCookieName(),
    value,
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: adminMaxAgeSeconds()
  });
  return res;
}
