import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { adminCookieName, verifyAdminCookieValue } from "@/lib/admin_auth";

export const config = {
  matcher: ["/admin/:path*", "/api/admin/:path*"]
};

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Allow the login endpoint/page through.
  if (pathname === "/admin/login" || pathname === "/api/admin/login") {
    return NextResponse.next();
  }

  const secret = process.env.ADMIN_COOKIE_SECRET || "";
  const cookie = req.cookies.get(adminCookieName())?.value;
  const ok = secret ? await verifyAdminCookieValue(secret, cookie) : false;
  if (ok) return NextResponse.next();

  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const proto = req.headers.get("x-forwarded-proto") || req.nextUrl.protocol.replace(":", "");
  const host = req.headers.get("x-forwarded-host") || req.headers.get("host") || req.nextUrl.host;
  const url = new URL("/admin/login", `${proto}://${host}`);
  url.searchParams.set("next", pathname);
  return NextResponse.redirect(url);
}

