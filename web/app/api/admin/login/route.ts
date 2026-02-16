import { NextResponse } from "next/server";

import { adminCookieName, adminMaxAgeSeconds, mintAdminCookieValue } from "@/lib/admin_auth";

export const runtime = "nodejs";

/** Build an absolute URL respecting X-Forwarded-* headers from a reverse proxy. */
function publicUrl(path: string, req: Request): URL {
  const h = new Headers(req.headers);
  const proto = h.get("x-forwarded-proto") || "https";
  const host = h.get("x-forwarded-host") || h.get("host") || new URL(req.url).host;
  return new URL(path, `${proto}://${host}`);
}

function badRedirect(req: Request, nextPath: string, err: string): NextResponse {
  const url = publicUrl("/admin/login", req);
  url.searchParams.set("next", nextPath);
  url.searchParams.set("err", err);
  return NextResponse.redirect(url, { status: 303 });
}

export async function GET(req: Request) {
  return NextResponse.redirect(publicUrl("/admin/login", req), { status: 303 });
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

  const value = await mintAdminCookieValue(secret);
  const res = NextResponse.redirect(publicUrl(nextPath, req), { status: 303 });
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
