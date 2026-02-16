import { NextResponse } from "next/server";

import { adminCookieName, adminMaxAgeSeconds, mintAdminCookieValue } from "@/lib/admin_auth";

export const runtime = "nodejs";

function badRedirect(reqUrl: string, nextPath: string, err: string): NextResponse {
  const url = new URL("/admin/login", reqUrl);
  url.searchParams.set("next", nextPath);
  url.searchParams.set("err", err);
  return NextResponse.redirect(url, { status: 303 });
}

export async function GET(req: Request) {
  // If someone opens the API route in the browser, send them to the login page.
  return NextResponse.redirect(new URL("/admin/login", req.url), { status: 303 });
}

export async function POST(req: Request) {
  // Avoid Request.formData() here: on some Vercel/Next runtimes this can throw and surface as a 500.
  // The form submits as application/x-www-form-urlencoded, so parse from text.
  const body = await req.text().catch(() => "");
  const params = new URLSearchParams(body);
  const password = String(params.get("password") ?? "");
  const nextRaw = String(params.get("next") ?? "/admin");
  const nextPath = nextRaw.startsWith("/") ? nextRaw : "/admin";

  const expected = process.env.ADMIN_PASSWORD || "";
  const secret = process.env.ADMIN_COOKIE_SECRET || "";
  if (!expected || !secret) {
    return badRedirect(req.url, nextPath, "Admin auth is not configured on the server.");
  }

  if (password !== expected) {
    return badRedirect(req.url, nextPath, "Invalid password.");
  }

  const value = await mintAdminCookieValue(secret);
  const res = NextResponse.redirect(new URL(nextPath, req.url), { status: 303 });
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
