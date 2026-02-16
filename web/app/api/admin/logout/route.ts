import { NextResponse } from "next/server";

import { adminCookieName } from "@/lib/admin_auth";

export const runtime = "nodejs";

export async function POST(req: Request) {
  const h = new Headers(req.headers);
  const proto = h.get("x-forwarded-proto") || "https";
  const host = h.get("x-forwarded-host") || h.get("host") || new URL(req.url).host;
  const res = NextResponse.redirect(new URL("/admin/login", `${proto}://${host}`), { status: 303 });
  res.cookies.set({
    name: adminCookieName(),
    value: "",
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: 0
  });
  return res;
}

