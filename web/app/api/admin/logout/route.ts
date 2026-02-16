import { NextResponse } from "next/server";

import { adminCookieName } from "@/lib/admin_auth";

export const runtime = "nodejs";

export async function POST(req: Request) {
  const h = (name: string) => req.headers.get(name);
  const proto = h("x-forwarded-proto") || new URL(req.url).protocol.replace(":", "");
  const host = h("x-forwarded-host") || h("host") || new URL(req.url).host;
  const origin = `${proto}://${host}`;

  const res = NextResponse.redirect(new URL("/admin/login", origin), { status: 303 });
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

